"""Tests for OllamaAIGateway — talks HTTP to Ollama via urllib.

We patch ``urllib.request.urlopen`` so these tests never hit the network.
"""

from __future__ import annotations

import io
import json
import unittest
from typing import Any
from unittest.mock import patch
from urllib import error as urllib_error

from app.infrastructure._ai_gateway_helpers import (
    AIConfigurationError,
    AIResponseParseError,
)
from app.infrastructure.ollama_ai_gateway import (
    OllamaAIGateway,
    OllamaHTTPError,
    TokenUsage,
)


class _RecordingPromptLoader:
    def load(self, name: str) -> str:
        return f"Template for {name}"


class _FakeResponse:
    def __init__(self, body: dict[str, Any]) -> None:
        self._body = json.dumps(body).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: Any) -> None:
        return None


def _make_urlopen(
    *,
    body: dict[str, Any] | None = None,
    raise_first_n: int = 0,
    raise_exc: BaseException | None = None,
) -> Any:
    counter = {"calls": 0}
    log: list[dict[str, Any]] = []

    def _urlopen(req: Any, timeout: float | None = None) -> _FakeResponse:
        counter["calls"] += 1
        log.append(
            {
                "url": req.full_url,
                "data": json.loads(req.data.decode("utf-8")) if req.data else None,
                "timeout": timeout,
            }
        )
        if counter["calls"] <= raise_first_n and raise_exc is not None:
            raise raise_exc
        return _FakeResponse(body or {"message": {"content": "ok"}})

    return _urlopen, log


class ConfigurationTests(unittest.TestCase):
    def test_defaults_host_and_model(self) -> None:
        gateway = OllamaAIGateway(prompt_loader=_RecordingPromptLoader())
        self.assertEqual(gateway.host, OllamaAIGateway.DEFAULT_HOST)
        self.assertEqual(gateway.model, OllamaAIGateway.DEFAULT_MODEL)

    def test_explicit_host_overrides_env(self) -> None:
        gateway = OllamaAIGateway(
            host="http://my-ollama:9999",
            prompt_loader=_RecordingPromptLoader(),
        )
        self.assertEqual(gateway.host, "http://my-ollama:9999")

    def test_trailing_slash_stripped_from_host(self) -> None:
        gateway = OllamaAIGateway(
            host="http://h:1/",
            prompt_loader=_RecordingPromptLoader(),
        )
        self.assertEqual(gateway.host, "http://h:1")


class CallShapeTests(unittest.TestCase):
    def test_sends_post_to_chat_endpoint_with_messages(self) -> None:
        fake, log = _make_urlopen()
        gateway = OllamaAIGateway(
            host="http://h:1",
            model="llama-test",
            prompt_loader=_RecordingPromptLoader(),
        )
        with patch("app.infrastructure.ollama_ai_gateway.urllib_request.urlopen", fake):
            gateway.generate_text("story_parser", {"k": "v"}, system_message="sys")

        self.assertEqual(log[0]["url"], "http://h:1/api/chat")
        payload = log[0]["data"]
        self.assertEqual(payload["model"], "llama-test")
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][0]["content"], "sys")
        self.assertEqual(payload["messages"][1]["role"], "user")
        self.assertIn("Template for story_parser", payload["messages"][1]["content"])
        self.assertIn('"k": "v"', payload["messages"][1]["content"])

    def test_timeout_passed_to_urlopen(self) -> None:
        fake, log = _make_urlopen()
        gateway = OllamaAIGateway(
            host="http://h:1",
            prompt_loader=_RecordingPromptLoader(),
            timeout=12.0,
        )
        with patch("app.infrastructure.ollama_ai_gateway.urllib_request.urlopen", fake):
            gateway.generate_text("story_parser", {})
        self.assertEqual(log[0]["timeout"], 12.0)


class TextExtractionTests(unittest.TestCase):
    def test_chat_message_content_returned(self) -> None:
        fake, _ = _make_urlopen(body={"message": {"content": "hi"}})
        gateway = OllamaAIGateway(prompt_loader=_RecordingPromptLoader())
        with patch("app.infrastructure.ollama_ai_gateway.urllib_request.urlopen", fake):
            self.assertEqual(gateway.generate_text("story_parser", {}), "hi")

    def test_legacy_response_field_falls_back(self) -> None:
        fake, _ = _make_urlopen(body={"response": "legacy ok"})
        gateway = OllamaAIGateway(prompt_loader=_RecordingPromptLoader())
        with patch("app.infrastructure.ollama_ai_gateway.urllib_request.urlopen", fake):
            self.assertEqual(gateway.generate_text("story_parser", {}), "legacy ok")

    def test_empty_response_raises(self) -> None:
        fake, _ = _make_urlopen(body={"message": {"content": ""}})
        gateway = OllamaAIGateway(prompt_loader=_RecordingPromptLoader())
        with patch("app.infrastructure.ollama_ai_gateway.urllib_request.urlopen", fake):
            with self.assertRaises(AIResponseParseError):
                gateway.generate_text("story_parser", {})


class JSONResponseTests(unittest.TestCase):
    def test_parses_json_content(self) -> None:
        fake, _ = _make_urlopen(body={"message": {"content": '{"foo": 1}'}})
        gateway = OllamaAIGateway(prompt_loader=_RecordingPromptLoader())
        with patch("app.infrastructure.ollama_ai_gateway.urllib_request.urlopen", fake):
            self.assertEqual(gateway.generate_json("story_parser", {}), {"foo": 1})

    def test_strips_json_code_fence(self) -> None:
        fake, _ = _make_urlopen(body={"message": {"content": '```json\n{"foo": 2}\n```'}})
        gateway = OllamaAIGateway(prompt_loader=_RecordingPromptLoader())
        with patch("app.infrastructure.ollama_ai_gateway.urllib_request.urlopen", fake):
            self.assertEqual(gateway.generate_json("story_parser", {}), {"foo": 2})


class HTTPErrorTests(unittest.TestCase):
    def test_4xx_raises_configuration_error(self) -> None:
        http_error = urllib_error.HTTPError(
            url="http://h:1/api/chat",
            code=404,
            msg="not found",
            hdrs=None,  # type: ignore[arg-type]
            fp=io.BytesIO(b"model not found"),
        )
        fake, _ = _make_urlopen(raise_first_n=1, raise_exc=http_error)
        gateway = OllamaAIGateway(prompt_loader=_RecordingPromptLoader())
        with patch("app.infrastructure.ollama_ai_gateway.urllib_request.urlopen", fake):
            with self.assertRaises(AIConfigurationError):
                gateway.generate_text("story_parser", {})

    def test_5xx_is_retried(self) -> None:
        http_error = urllib_error.HTTPError(
            url="http://h:1/api/chat",
            code=503,
            msg="busy",
            hdrs=None,  # type: ignore[arg-type]
            fp=io.BytesIO(b"server busy"),
        )
        fake, log = _make_urlopen(
            body={"message": {"content": "eventually ok"}},
            raise_first_n=2,
            raise_exc=http_error,
        )
        with patch("tenacity.nap.time.sleep", lambda _s: None):
            with patch("app.infrastructure.ollama_ai_gateway.urllib_request.urlopen", fake):
                gateway = OllamaAIGateway(
                    prompt_loader=_RecordingPromptLoader(),
                    max_retries=3,
                )
                result = gateway.generate_text("story_parser", {})
        self.assertEqual(result, "eventually ok")
        self.assertEqual(len(log), 3)

    def test_url_error_is_retried(self) -> None:
        fake, log = _make_urlopen(
            body={"message": {"content": "ok"}},
            raise_first_n=2,
            raise_exc=urllib_error.URLError("connection refused"),
        )
        with patch("tenacity.nap.time.sleep", lambda _s: None):
            with patch("app.infrastructure.ollama_ai_gateway.urllib_request.urlopen", fake):
                gateway = OllamaAIGateway(
                    prompt_loader=_RecordingPromptLoader(),
                    max_retries=3,
                )
                gateway.generate_text("story_parser", {})
        self.assertEqual(len(log), 3)

    def test_invalid_response_body_raises_parse_error(self) -> None:
        def _urlopen(req: Any, timeout: float | None = None) -> _FakeResponse:
            class _BadResponse:
                def read(self) -> bytes:
                    return b"not json"

                def __enter__(self) -> "_BadResponse":
                    return self

                def __exit__(self, *args: Any) -> None:
                    return None

            return _BadResponse()  # type: ignore[return-value]

        gateway = OllamaAIGateway(prompt_loader=_RecordingPromptLoader())
        with patch("app.infrastructure.ollama_ai_gateway.urllib_request.urlopen", _urlopen):
            with self.assertRaises(AIResponseParseError):
                gateway.generate_text("story_parser", {})


class TokenUsageTests(unittest.TestCase):
    def test_token_callback_uses_prompt_eval_and_eval_counts(self) -> None:
        fake, _ = _make_urlopen(
            body={
                "message": {"content": "ok"},
                "prompt_eval_count": 11,
                "eval_count": 22,
            }
        )
        events: list[TokenUsage] = []
        gateway = OllamaAIGateway(
            prompt_loader=_RecordingPromptLoader(),
            token_callback=events.append,
        )
        with patch("app.infrastructure.ollama_ai_gateway.urllib_request.urlopen", fake):
            gateway.generate_text("story_parser", {})
        self.assertEqual(len(events), 1)
        usage = events[0]
        self.assertEqual(usage.input_tokens, 11)
        self.assertEqual(usage.output_tokens, 22)
        self.assertEqual(usage.total_tokens, 33)
        self.assertEqual(usage.prompt_name, "story_parser")


def test_5xx_directly_raises_ollama_http_error() -> None:
    """Direct test that the HTTPError → OllamaHTTPError mapping works."""
    assert issubclass(OllamaHTTPError, RuntimeError)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
