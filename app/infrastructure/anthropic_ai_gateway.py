"""Optional Anthropic (Claude)-backed implementation of the AI gateway.

Mirrors :class:`OpenAIAIGateway`: retry on transient errors, configurable
timeout, optional token-usage callback, and graceful fallback when the
optional ``anthropic`` SDK isn't installed.
"""

from __future__ import annotations

import logging
import os
from typing import Any

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

__all__ = [
    "AnthropicAIGateway",
    "AIConfigurationError",
    "AIResponseParseError",
    "TokenCallback",
    "TokenUsage",
]


def _resolve_retryable_exceptions() -> tuple[type[BaseException], ...]:
    """Return Anthropic exception classes worth retrying.

    Falls back to ``(Exception,)`` if the anthropic package isn't installed,
    so the gateway can be imported and unit-tested without the optional dep.
    """
    try:
        from anthropic import (
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


class AnthropicAIGateway(AIGateway):
    DEFAULT_MODEL = "claude-sonnet-4-5"
    DEFAULT_TIMEOUT_SECONDS = 30.0
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_MAX_TOKENS = 4096

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        prompt_loader: PromptTemplateLoader | None = None,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        max_tokens: int | None = None,
        token_callback: TokenCallback | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise AIConfigurationError(
                "Real AI mode requires an Anthropic API key. "
                "Pass one explicitly or set ANTHROPIC_API_KEY."
            )

        self.model = model or os.environ.get("ANTHROPIC_MODEL") or self.DEFAULT_MODEL
        self.prompt_loader = prompt_loader or PromptTemplateLoader()
        self.timeout = float(timeout) if timeout is not None else self.DEFAULT_TIMEOUT_SECONDS
        self.max_retries = int(max_retries) if max_retries is not None else self.DEFAULT_MAX_RETRIES
        self.max_tokens = int(max_tokens) if max_tokens is not None else self.DEFAULT_MAX_TOKENS
        self.token_callback = token_callback
        self._active_prompt_name: str | None = None

    def generate_text(
        self,
        prompt_name: str,
        input_data: dict[str, Any],
        system_message: str | None = None,
    ) -> str:
        template = self.prompt_loader.load(prompt_name)
        prompt = build_prompt(template, input_data)
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
        return parse_json_response(text, prompt_name, provider_label="Anthropic")

    def _call_with_retry(
        self,
        prompt: str,
        system_message: str | None,
    ) -> str:
        try:
            from tenacity import (
                retry,
                retry_if_exception_type,
                stop_after_attempt,
                wait_exponential,
            )
        except ImportError:
            logger.warning(
                "tenacity not installed; Anthropic gateway will not retry on "
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
            from anthropic import Anthropic
        except ImportError as exc:
            raise AIConfigurationError(
                "Real AI mode requires the optional Anthropic Python package."
            ) from exc

        client = Anthropic(api_key=self.api_key, timeout=self.timeout)
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_message:
            kwargs["system"] = system_message

        response = client.messages.create(**kwargs)
        self._emit_usage(response)
        return self._extract_text(response)

    def _emit_usage(self, response: Any) -> None:
        if self.token_callback is None:
            return
        prompt_name = getattr(self, "_active_prompt_name", None) or ""
        usage = getattr(response, "usage", None)
        if usage is None and isinstance(response, dict):
            usage = response.get("usage")
        if usage is None:
            return

        def _read(name: str) -> int:
            value = getattr(usage, name, None) if not isinstance(usage, dict) else usage.get(name)
            if value is None:
                return 0
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0

        input_tokens = _read("input_tokens")
        output_tokens = _read("output_tokens")
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
        # Anthropic messages.create returns content as a list of blocks; for our
        # text-only prompts the first text block carries the full reply.
        content = getattr(response, "content", None)
        if content is None and isinstance(response, dict):
            content = response.get("content")
        if not content:
            raise AIResponseParseError("Anthropic response did not contain content blocks.")

        chunks: list[str] = []
        for block in content:
            block_type = (
                getattr(block, "type", None) if not isinstance(block, dict) else block.get("type")
            )
            if block_type and block_type != "text":
                continue
            text = (
                getattr(block, "text", None) if not isinstance(block, dict) else block.get("text")
            )
            if isinstance(text, str):
                chunks.append(text)

        joined = "".join(chunks).strip()
        if not joined:
            raise AIResponseParseError("Anthropic response did not contain text output.")
        return joined
