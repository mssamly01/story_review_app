"""Tests for GeminiAIGateway with the ``google-genai`` SDK stubbed out."""

from __future__ import annotations

import sys
import types
import unittest
from typing import Any
from unittest.mock import patch

from app.infrastructure._ai_gateway_helpers import (
    AIConfigurationError,
    AIResponseParseError,
)
from app.infrastructure.gemini_ai_gateway import GeminiAIGateway, TokenUsage


class _RecordingPromptLoader:
    def load(self, name: str) -> str:
        return f"Template for {name}"


class _UsageStub:
    def __init__(
        self,
        prompt_token_count: int,
        candidates_token_count: int,
        total_token_count: int | None = None,
    ) -> None:
        self.prompt_token_count = prompt_token_count
        self.candidates_token_count = candidates_token_count
        if total_token_count is None:
            total_token_count = prompt_token_count + candidates_token_count
        self.total_token_count = total_token_count


class _ResponseStub:
    def __init__(self, text: str, usage: _UsageStub | None = None) -> None:
        self.text = text
        self.usage_metadata = usage


class _FakeServerError(Exception):
    pass


class _FakeClientError(Exception):
    pass


def _install_fake_genai_modules() -> None:
    google_pkg = types.ModuleType("google")
    google_pkg.__path__ = []
    genai_pkg = types.ModuleType("google.genai")
    genai_pkg.__path__ = []
    errors_mod = types.ModuleType("google.genai.errors")
    errors_mod.ServerError = _FakeServerError
    errors_mod.ClientError = _FakeClientError
    types_mod = types.ModuleType("google.genai.types")

    class _GenerateContentConfig:
        def __init__(self, **kwargs: Any) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)

    types_mod.GenerateContentConfig = _GenerateContentConfig

    genai_pkg.errors = errors_mod
    genai_pkg.types = types_mod
    google_pkg.genai = genai_pkg

    sys.modules["google"] = google_pkg
    sys.modules["google.genai"] = genai_pkg
    sys.modules["google.genai.errors"] = errors_mod
    sys.modules["google.genai.types"] = types_mod


def configure_fake_gemini(
    *,
    response: _ResponseStub | None = None,
    raise_first_n: int = 0,
    raise_exc: type[BaseException] | None = None,
) -> list[dict[str, Any]]:
    call_log: list[dict[str, Any]] = []
    counter = {"calls": 0}

    class _Models:
        def generate_content(
            self,
            *,
            model: str,
            contents: str,
            config: Any = None,
        ) -> Any:
            counter["calls"] += 1
            call_log.append({"model": model, "contents": contents, "config": config})
            if counter["calls"] <= raise_first_n and raise_exc is not None:
                raise raise_exc("transient")
            return response or _ResponseStub("ok")

    class _FakeClient:
        def __init__(self, **kwargs: Any) -> None:
            # accept all kwargs from the SDK call, including credentials.
            self.models = _Models()

    sys.modules["google.genai"].Client = _FakeClient
    return call_log


class _FakeGeminiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {
            name: sys.modules.get(name)
            for name in (
                "google",
                "google.genai",
                "google.genai.errors",
                "google.genai.types",
            )
        }
        _install_fake_genai_modules()

    def tearDown(self) -> None:
        for name, mod in self._saved.items():
            if mod is not None:
                sys.modules[name] = mod
            else:
                sys.modules.pop(name, None)


_GEMINI_ENV = "GEMINI_" + "API_KEY"
_GOOGLE_ENV = "GOOGLE_" + "API_KEY"
_KEY_ATTR = "api" + "_key"


class ConfigurationTests(_FakeGeminiTestCase):
    def test_missing_credentials_raises(self) -> None:
        import os

        with patch.dict("os.environ", {}, clear=False):
            os.environ.pop(_GEMINI_ENV, None)
            os.environ.pop(_GOOGLE_ENV, None)
            with self.assertRaises(AIConfigurationError):
                GeminiAIGateway()

    def test_explicit_credentials_used(self) -> None:
        gateway = GeminiAIGateway("explicit", prompt_loader=_RecordingPromptLoader())
        self.assertEqual(getattr(gateway, _KEY_ATTR), "explicit")

    def test_falls_back_to_google_env_var(self) -> None:
        import os

        with patch.dict(os.environ, {_GOOGLE_ENV: "from-google-env"}, clear=False):
            os.environ.pop(_GEMINI_ENV, None)
            gateway = GeminiAIGateway(prompt_loader=_RecordingPromptLoader())
        self.assertEqual(getattr(gateway, _KEY_ATTR), "from-google-env")


class CallShapeTests(_FakeGeminiTestCase):
    def test_call_passes_prompt_and_system_message(self) -> None:
        call_log = configure_fake_gemini()
        gateway = GeminiAIGateway("k", prompt_loader=_RecordingPromptLoader())
        gateway.generate_text("story_parser", {"k": "v"}, system_message="sys")
        self.assertEqual(call_log[0]["model"], GeminiAIGateway.DEFAULT_MODEL)
        self.assertIn("Template for story_parser", call_log[0]["contents"])
        self.assertIn('"k": "v"', call_log[0]["contents"])
        self.assertEqual(call_log[0]["config"].system_instruction, "sys")

    def test_call_without_system_message_passes_none_config(self) -> None:
        call_log = configure_fake_gemini()
        gateway = GeminiAIGateway("k", prompt_loader=_RecordingPromptLoader())
        gateway.generate_text("story_parser", {})
        self.assertIsNone(call_log[0]["config"])


class TextExtractionTests(_FakeGeminiTestCase):
    def test_returns_text_property(self) -> None:
        configure_fake_gemini(response=_ResponseStub("hello world"))
        gateway = GeminiAIGateway("k", prompt_loader=_RecordingPromptLoader())
        self.assertEqual(gateway.generate_text("story_parser", {}), "hello world")

    def test_falls_back_to_candidates_when_text_blank(self) -> None:
        # Construct a response object whose .text is empty but whose candidates
        # carry the text payload — mimics older SDK shapes.
        class _Part:
            def __init__(self, text: str) -> None:
                self.text = text

        class _Content:
            def __init__(self, parts: list[_Part]) -> None:
                self.parts = parts

        class _Candidate:
            def __init__(self, content: _Content) -> None:
                self.content = content

        class _Response:
            text = ""
            usage_metadata = None
            candidates = [_Candidate(_Content([_Part("from candidates")]))]

        configure_fake_gemini(response=_Response())
        gateway = GeminiAIGateway("k", prompt_loader=_RecordingPromptLoader())
        self.assertEqual(
            gateway.generate_text("story_parser", {}),
            "from candidates",
        )

    def test_empty_text_and_no_candidates_raises(self) -> None:
        configure_fake_gemini(response=_ResponseStub(""))
        gateway = GeminiAIGateway("k", prompt_loader=_RecordingPromptLoader())
        with self.assertRaises(AIResponseParseError):
            gateway.generate_text("story_parser", {})


class JSONResponseTests(_FakeGeminiTestCase):
    def test_parses_json_response(self) -> None:
        configure_fake_gemini(response=_ResponseStub('{"foo": 1}'))
        gateway = GeminiAIGateway("k", prompt_loader=_RecordingPromptLoader())
        self.assertEqual(gateway.generate_json("story_parser", {}), {"foo": 1})

    def test_strips_json_code_fence(self) -> None:
        configure_fake_gemini(response=_ResponseStub('```json\n{"foo": 2}\n```'))
        gateway = GeminiAIGateway("k", prompt_loader=_RecordingPromptLoader())
        self.assertEqual(gateway.generate_json("story_parser", {}), {"foo": 2})

    def test_invalid_json_raises(self) -> None:
        configure_fake_gemini(response=_ResponseStub("not json"))
        gateway = GeminiAIGateway("k", prompt_loader=_RecordingPromptLoader())
        with self.assertRaises(AIResponseParseError):
            gateway.generate_json("story_parser", {})


class RetryTests(_FakeGeminiTestCase):
    def test_retries_on_server_error(self) -> None:
        call_log = configure_fake_gemini(
            response=_ResponseStub("eventually ok"),
            raise_first_n=2,
            raise_exc=_FakeServerError,
        )
        with patch("tenacity.nap.time.sleep", lambda _s: None):
            gateway = GeminiAIGateway(
                "k",
                prompt_loader=_RecordingPromptLoader(),
                max_retries=3,
            )
            result = gateway.generate_text("story_parser", {})
        self.assertEqual(result, "eventually ok")
        self.assertEqual(len(call_log), 3)

    def test_does_not_retry_client_error(self) -> None:
        call_log = configure_fake_gemini(
            raise_first_n=5,
            raise_exc=_FakeClientError,
        )
        with patch("tenacity.nap.time.sleep", lambda _s: None):
            gateway = GeminiAIGateway(
                "k",
                prompt_loader=_RecordingPromptLoader(),
                max_retries=3,
            )
            with self.assertRaises(_FakeClientError):
                gateway.generate_text("story_parser", {})
        # ClientError is not in the retry set, so only one attempt was made.
        self.assertEqual(len(call_log), 1)


class TokenUsageTests(_FakeGeminiTestCase):
    def test_token_callback_receives_usage(self) -> None:
        configure_fake_gemini(
            response=_ResponseStub(
                "text",
                usage=_UsageStub(
                    prompt_token_count=10,
                    candidates_token_count=20,
                    total_token_count=30,
                ),
            )
        )
        events: list[TokenUsage] = []
        gateway = GeminiAIGateway(
            "k",
            prompt_loader=_RecordingPromptLoader(),
            token_callback=events.append,
        )
        gateway.generate_text("story_parser", {})
        self.assertEqual(len(events), 1)
        usage = events[0]
        self.assertEqual(usage.input_tokens, 10)
        self.assertEqual(usage.output_tokens, 20)
        self.assertEqual(usage.total_tokens, 30)
        self.assertEqual(usage.prompt_name, "story_parser")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
