"""Optional Google Gemini-backed implementation of the AI gateway.

Wraps the ``google-genai`` SDK with the same retry / timeout / token-tracking
contract as :class:`OpenAIAIGateway`. The SDK is an optional install so this
module is safe to import even when ``google-genai`` is not present.
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
    "GeminiAIGateway",
    "AIConfigurationError",
    "AIResponseParseError",
    "TokenCallback",
    "TokenUsage",
]


def _resolve_retryable_exceptions() -> tuple[type[BaseException], ...]:
    """Return Gemini exception classes worth retrying.

    The ``google-genai`` SDK uses ``ServerError`` for transient 5xx responses
    and the base ``APIError`` covers other server-side issues. We retry
    ``ServerError`` only — ``ClientError`` is usually a permanent 4xx that
    won't recover from retries.
    """
    try:
        from google.genai.errors import ServerError
    except ImportError:
        return (Exception,)
    return (ServerError,)


class GeminiAIGateway(AIGateway):
    DEFAULT_MODEL = "gemini-2.5-flash"
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
    ) -> None:
        self.api_key = (
            api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        )
        if not self.api_key:
            raise AIConfigurationError(
                "Real AI mode requires a Gemini API key. "
                "Pass one explicitly or set GEMINI_API_KEY / GOOGLE_API_KEY."
            )

        self.model = model or os.environ.get("GEMINI_MODEL") or self.DEFAULT_MODEL
        self.prompt_loader = prompt_loader or PromptTemplateLoader()
        self.timeout = float(timeout) if timeout is not None else self.DEFAULT_TIMEOUT_SECONDS
        self.max_retries = int(max_retries) if max_retries is not None else self.DEFAULT_MAX_RETRIES
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
        return parse_json_response(text, prompt_name, provider_label="Gemini")

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
                "tenacity not installed; Gemini gateway will not retry on "
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
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise AIConfigurationError(
                "Real AI mode requires the optional google-genai Python package."
            ) from exc

        client = genai.Client(api_key=self.api_key)
        config_kwargs: dict[str, Any] = {}
        if system_message:
            config_kwargs["system_instruction"] = system_message
        config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None

        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        self._emit_usage(response)
        return self._extract_text(response)

    def _emit_usage(self, response: Any) -> None:
        if self.token_callback is None:
            return
        prompt_name = getattr(self, "_active_prompt_name", None) or ""
        usage = getattr(response, "usage_metadata", None)
        if usage is None and isinstance(response, dict):
            usage = response.get("usage_metadata") or response.get("usage")
        if usage is None:
            return

        def _read(*names: str) -> int:
            for name in names:
                value = (
                    getattr(usage, name, None) if not isinstance(usage, dict) else usage.get(name)
                )
                if value is None:
                    continue
                try:
                    return int(value)
                except (TypeError, ValueError):
                    continue
            return 0

        input_tokens = _read("prompt_token_count", "input_tokens")
        output_tokens = _read("candidates_token_count", "output_tokens")
        total_tokens = _read("total_token_count", "total_tokens")
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
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text

        if isinstance(response, dict):
            text = response.get("text")
            if isinstance(text, str) and text.strip():
                return text

        candidates = getattr(response, "candidates", None)
        if candidates is None and isinstance(response, dict):
            candidates = response.get("candidates")
        if candidates:
            for candidate in candidates:
                content = (
                    getattr(candidate, "content", None)
                    if not isinstance(candidate, dict)
                    else candidate.get("content")
                )
                if content is None:
                    continue
                parts = (
                    getattr(content, "parts", None)
                    if not isinstance(content, dict)
                    else content.get("parts")
                )
                if not parts:
                    continue
                chunks: list[str] = []
                for part in parts:
                    part_text = (
                        getattr(part, "text", None)
                        if not isinstance(part, dict)
                        else part.get("text")
                    )
                    if isinstance(part_text, str):
                        chunks.append(part_text)
                if chunks:
                    return "".join(chunks).strip()

        raise AIResponseParseError("Gemini response did not contain text output.")
