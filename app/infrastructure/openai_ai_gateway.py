"""Optional OpenAI-backed implementation of the AI gateway.

Production-ready features:

* Timeout — every request has a deadline (default 30s).
* Retry — transient errors (timeout, rate limit, 5xx) are retried with
  exponential backoff using ``tenacity``.
* Token tracking — an optional callback receives a ``TokenUsage`` record after
  every successful call so the application can log usage or aggregate cost.
* Streaming — opt-in via the ``stream`` flag; falls back to a non-streaming
  call when the underlying SDK doesn't support it.

The gateway still implements the lean ``AIGateway`` protocol so callers don't
need to know whether they're talking to OpenAI, the mock, or anything else.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Iterable

from app.infrastructure._ai_gateway_helpers import (
    AIConfigurationError,
    AIResponseParseError,
    TokenCallback,
    TokenUsage,
    build_prompt,
    parse_json_response,
)
from app.infrastructure.ai_gateway import AIGateway
from app.infrastructure.prompt_template_loader import PromptTemplateLoader

logger = logging.getLogger(__name__)

# Re-export so callers that previously imported these from this module keep working.
__all__ = [
    "AIConfigurationError",
    "AIResponseParseError",
    "OpenAIAIGateway",
    "TokenCallback",
    "TokenUsage",
]


def _resolve_retryable_exceptions() -> tuple[type[BaseException], ...]:
    """Return the OpenAI exception classes worth retrying.

    Falls back to ``(Exception,)`` if the openai package isn't installed yet,
    so the gateway can be imported and unit-tested without the optional dep.
    """
    try:
        from openai import (
            APIConnectionError,
            APITimeoutError,
            InternalServerError,
            RateLimitError,
        )
    except ImportError:
        return (Exception,)
    return (
        APIConnectionError,
        APITimeoutError,
        InternalServerError,
        RateLimitError,
    )


class OpenAIAIGateway(AIGateway):
    DEFAULT_MODEL = "gpt-4.1-mini"
    DEFAULT_TIMEOUT_SECONDS = 30.0
    DEFAULT_MAX_RETRIES = 3

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        prompt_loader: PromptTemplateLoader | None = None,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        token_callback: TokenCallback | None = None,
        stream: bool = False,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise AIConfigurationError(
                "Real AI mode requires an OpenAI API key. "
                "Pass one explicitly or set OPENAI_API_KEY."
            )

        self.model = model or os.environ.get("OPENAI_MODEL") or self.DEFAULT_MODEL
        self.prompt_loader = prompt_loader or PromptTemplateLoader()
        self.timeout = float(timeout) if timeout is not None else self.DEFAULT_TIMEOUT_SECONDS
        self.max_retries = int(max_retries) if max_retries is not None else self.DEFAULT_MAX_RETRIES
        self.token_callback = token_callback
        self.stream = stream
        self._active_prompt_name: str | None = None

    def generate_text(
        self,
        prompt_name: str,
        input_data: dict[str, Any],
        system_message: str | None = None,
    ) -> str:
        template = self.prompt_loader.load(prompt_name)
        prompt = self._build_prompt(template, input_data)
        self._active_prompt_name = prompt_name
        try:
            return self._call_with_retry(prompt, system_message)
        finally:
            self._active_prompt_name = None

    def generate_json(
        self,
        prompt_name: str,
        input_data: dict[str, Any],
        system_message: str | None = None,
    ) -> dict[str, Any]:
        text = self.generate_text(prompt_name, input_data, system_message)
        return self._parse_json(text, prompt_name)

    def _build_prompt(self, template: str, input_data: dict[str, Any]) -> str:
        return build_prompt(template, input_data)

    def _call_with_retry(
        self,
        prompt: str,
        system_message: str | None,
    ) -> str:
        """Wrap ``_call_model`` with tenacity-based exponential backoff.

        Falls back to a single no-retry call if ``tenacity`` isn't installed.
        """
        try:
            from tenacity import (
                retry,
                retry_if_exception_type,
                stop_after_attempt,
                wait_exponential,
            )
        except ImportError:
            logger.warning(
                "tenacity not installed; OpenAI gateway will not retry on "
                "transient errors. Install requirements-ai.txt for retry support."
            )
            return self._call_model(prompt, system_message)

        retryable = _resolve_retryable_exceptions()
        attempts = max(1, self.max_retries)

        @retry(
            reraise=True,
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(retryable),
        )
        def _do_call() -> str:
            return self._call_model(prompt, system_message)

        return _do_call()

    def _call_model(
        self,
        prompt: str,
        system_message: str | None,
    ) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise AIConfigurationError(
                "Real AI mode requires the optional OpenAI Python package."
            ) from exc

        client = OpenAI(api_key=self.api_key, timeout=self.timeout)
        messages: list[dict[str, str]] = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        if self.stream:
            return self._call_streaming(client, messages)

        response = client.responses.create(
            model=self.model,
            input=messages,
        )
        self._emit_usage(response)
        return self._extract_text(response)

    def _call_streaming(
        self,
        client: Any,
        messages: list[dict[str, str]],
    ) -> str:
        try:
            stream_ctx = client.responses.stream(
                model=self.model,
                input=messages,
            )
        except (AttributeError, TypeError):
            response = client.responses.create(
                model=self.model,
                input=messages,
            )
            self._emit_usage(response)
            return self._extract_text(response)

        chunks: list[str] = []
        with stream_ctx as stream:
            for event in self._iter_stream_events(stream):
                delta = getattr(event, "delta", None) or getattr(event, "text", None)
                if isinstance(delta, str):
                    chunks.append(delta)
            final = stream.get_final_response()
        self._emit_usage(final)
        if chunks:
            return "".join(chunks).strip()
        return self._extract_text(final)

    def _iter_stream_events(self, stream: Any) -> Iterable[Any]:
        for attr in ("text_deltas", "events", "__iter__"):
            iterator = getattr(stream, attr, None)
            if callable(iterator):
                try:
                    return iterator()
                except TypeError:
                    continue
        return iter([])

    def _emit_usage(self, response: Any) -> None:
        if self.token_callback is None:
            return
        prompt_name = getattr(self, "_active_prompt_name", None) or ""
        usage = getattr(response, "usage", None)
        if usage is None and isinstance(response, dict):
            usage = response.get("usage")
        if usage is None:
            return

        def _read(name: str, fallback: str) -> int:
            for source in (usage, response):
                value = (
                    getattr(source, name, None)
                    if not isinstance(source, dict)
                    else source.get(name)
                )
                if value is not None:
                    try:
                        return int(value)
                    except (TypeError, ValueError):
                        pass
                fb = (
                    getattr(source, fallback, None)
                    if not isinstance(source, dict)
                    else source.get(fallback)
                )
                if fb is not None:
                    try:
                        return int(fb)
                    except (TypeError, ValueError):
                        pass
            return 0

        input_tokens = _read("input_tokens", "prompt_tokens")
        output_tokens = _read("output_tokens", "completion_tokens")
        total_tokens = _read("total_tokens", "total_tokens")
        if total_tokens == 0:
            total_tokens = input_tokens + output_tokens
        try:
            self.token_callback(
                TokenUsage(
                    prompt_name=prompt_name,
                    model=self.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                )
            )
        except Exception:  # pragma: no cover - callback errors must not break call
            logger.exception("token_callback raised; swallowing to protect call")

    def _extract_text(self, response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        if isinstance(response, dict):
            output_text = response.get("output_text")
            if isinstance(output_text, str) and output_text.strip():
                return output_text
            choices = response.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content")
                if isinstance(content, str) and content.strip():
                    return content

        choices = getattr(response, "choices", None)
        if choices:
            message = getattr(choices[0], "message", None)
            content = getattr(message, "content", None)
            if isinstance(content, str) and content.strip():
                return content

        raise AIResponseParseError("OpenAI response did not contain text output.")

    def _parse_json(self, text: str, prompt_name: str) -> dict[str, Any]:
        return parse_json_response(text, prompt_name, provider_label="OpenAI")
