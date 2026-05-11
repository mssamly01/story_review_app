"""Optional Ollama-backed implementation of the AI gateway.

Ollama runs as a local HTTP server (default ``http://localhost:11434``) and
exposes an OpenAI-compatible chat API. We talk to it via :mod:`urllib` so
the gateway has no additional package dependency beyond the standard library.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

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
    "OllamaAIGateway",
    "OllamaHTTPError",
    "AIConfigurationError",
    "AIResponseParseError",
    "TokenCallback",
    "TokenUsage",
]


class OllamaHTTPError(RuntimeError):
    """Raised when the Ollama HTTP endpoint returns a non-2xx response."""

    def __init__(self, status_code: int, body: str) -> None:
        super().__init__(f"Ollama HTTP {status_code}: {body[:200]}")
        self.status_code = status_code
        self.body = body


def _resolve_retryable_exceptions() -> tuple[type[BaseException], ...]:
    """Transient network errors plus 5xx responses are worth retrying."""
    return (
        urllib_error.URLError,
        TimeoutError,
        ConnectionError,
        OllamaHTTPError,
    )


class OllamaAIGateway(AIGateway):
    DEFAULT_HOST = "http://localhost:11434"
    DEFAULT_MODEL = "llama3.2"
    DEFAULT_TIMEOUT_SECONDS = 60.0
    DEFAULT_MAX_RETRIES = 3

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        prompt_loader: PromptTemplateLoader | None = None,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        token_callback: TokenCallback | None = None,
    ) -> None:
        self.host = (host or os.environ.get("OLLAMA_HOST") or self.DEFAULT_HOST).rstrip("/")
        self.model = model or os.environ.get("OLLAMA_MODEL") or self.DEFAULT_MODEL
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
        return parse_json_response(text, prompt_name, provider_label="Ollama")

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
                "tenacity not installed; Ollama gateway will not retry on "
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
        messages: list[dict[str, str]] = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        response = self._post_json(f"{self.host}/api/chat", payload)
        self._emit_usage(response)
        return self._extract_text(response)

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = urllib_request.Request(  # noqa: S310 - configurable host, not user input
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib_request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                raw = resp.read().decode("utf-8")
        except urllib_error.HTTPError as exc:
            body_text = ""
            try:
                body_text = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            if 500 <= exc.code < 600:
                raise OllamaHTTPError(exc.code, body_text) from exc
            raise AIConfigurationError(
                f"Ollama returned HTTP {exc.code}: {body_text[:200]}"
            ) from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AIResponseParseError("Ollama response body was not valid JSON.") from exc

        if not isinstance(data, dict):
            raise AIResponseParseError("Ollama response root was not a JSON object.")
        return data

    def _emit_usage(self, response: dict[str, Any]) -> None:
        if self.token_callback is None:
            return
        prompt_name = getattr(self, "_active_prompt_name", None) or ""
        input_tokens = int(response.get("prompt_eval_count") or 0)
        output_tokens = int(response.get("eval_count") or 0)
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

    def _extract_text(self, response: dict[str, Any]) -> str:
        message = response.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content

        content = response.get("response")
        if isinstance(content, str) and content.strip():
            return content

        raise AIResponseParseError("Ollama response did not contain text output.")
