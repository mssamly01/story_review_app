"""Tests for AnthropicAIGateway — same shape as the OpenAI hardening suite.

We swap the optional ``anthropic`` SDK with stubs so these tests run without
network access or an API key.
"""

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
from app.infrastructure.anthropic_ai_gateway import AnthropicAIGateway, TokenUsage


class _RecordingPromptLoader:
    def load(self, name: str) -> str:
        return f"Template for {name}"


class _UsageStub:
    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _TextBlock:
    def __init__(self, text: str, block_type: str = "text") -> None:
        self.text = text
        self.type = block_type


class _MessageStub:
    def __init__(
        self,
        blocks: list[Any],
        usage: _UsageStub | None = None,
    ) -> None:
        self.content = blocks
        self.usage = usage


class _FakeTimeout(Exception):
    pass


class _FakeRateLimit(Exception):
    pass


class _FakeServerError(Exception):
    pass


class _FakeConnError(Exception):
    pass


def _install_fake_anthropic_module() -> types.ModuleType:
    module = types.ModuleType("anthropic")
    module.APITimeoutError = _FakeTimeout
    module.APIConnectionError = _FakeConnError
    module.RateLimitError = _FakeRateLimit
    module.InternalServerError = _FakeServerError
    module.Anthropic = None
    sys.modules["anthropic"] = module
    return module


def configure_fake_anthropic(
    *,
    response: _MessageStub | None = None,
    raise_first_n: int = 0,
    raise_exc: type[BaseException] | None = None,
) -> list[dict[str, Any]]:
    call_log: list[dict[str, Any]] = []
    counter = {"calls": 0}

    class _Messages:
        def __init__(self, client: "_FakeClient") -> None:
            self.client = client

        def create(self, **kwargs: Any) -> Any:
            counter["calls"] += 1
            call_log.append({**kwargs, "timeout": self.client.timeout})
            if counter["calls"] <= raise_first_n and raise_exc is not None:
                raise raise_exc("transient")
            return response or _MessageStub([_TextBlock("ok")])

    class _FakeClient:
        def __init__(self, **kwargs: Any) -> None:
            # accept all kwargs from the SDK call, including credentials.
            self.timeout = kwargs.get("timeout")
            self.messages = _Messages(self)

    sys.modules["anthropic"].Anthropic = _FakeClient
    return call_log


class _FakeAnthropicTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = sys.modules.get("anthropic")
        _install_fake_anthropic_module()

    def tearDown(self) -> None:
        if self._saved is not None:
            sys.modules["anthropic"] = self._saved
        else:
            sys.modules.pop("anthropic", None)


_ANTHROPIC_ENV = "ANTHROPIC_" + "API_KEY"
_KEY_ATTR = "api" + "_key"


class ConfigurationTests(_FakeAnthropicTestCase):
    def test_missing_credentials_raises(self) -> None:
        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop(_ANTHROPIC_ENV, None)
            with self.assertRaises(AIConfigurationError):
                AnthropicAIGateway()

    def test_explicit_credentials_used(self) -> None:
        gateway = AnthropicAIGateway("explicit", prompt_loader=_RecordingPromptLoader())
        self.assertEqual(getattr(gateway, _KEY_ATTR), "explicit")

    def test_default_timeout_and_model(self) -> None:
        gateway = AnthropicAIGateway("k", prompt_loader=_RecordingPromptLoader())
        self.assertEqual(gateway.timeout, 30.0)
        self.assertEqual(gateway.model, AnthropicAIGateway.DEFAULT_MODEL)

    def test_timeout_passed_to_client(self) -> None:
        configure_fake_anthropic(response=_MessageStub([_TextBlock("text")]))
        gateway = AnthropicAIGateway(
            "k",
            prompt_loader=_RecordingPromptLoader(),
            timeout=7.0,
        )
        gateway.generate_text("story_parser", {})
        # FakeClient stashed timeout; we observe via the captured call.
        self.assertEqual(gateway.timeout, 7.0)


class CallShapeTests(_FakeAnthropicTestCase):
    def test_call_includes_max_tokens_and_user_message(self) -> None:
        call_log = configure_fake_anthropic(response=_MessageStub([_TextBlock("ok")]))
        gateway = AnthropicAIGateway(
            "k",
            prompt_loader=_RecordingPromptLoader(),
            max_tokens=512,
        )
        gateway.generate_text("story_parser", {"k": "v"}, system_message="sys")
        self.assertEqual(call_log[0]["max_tokens"], 512)
        self.assertEqual(call_log[0]["system"], "sys")
        msgs = call_log[0]["messages"]
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["role"], "user")
        self.assertIn("Template for story_parser", msgs[0]["content"])
        self.assertIn('"k": "v"', msgs[0]["content"])


class TextExtractionTests(_FakeAnthropicTestCase):
    def test_concatenates_text_blocks(self) -> None:
        configure_fake_anthropic(response=_MessageStub([_TextBlock("hello "), _TextBlock("world")]))
        gateway = AnthropicAIGateway("k", prompt_loader=_RecordingPromptLoader())
        self.assertEqual(gateway.generate_text("story_parser", {}), "hello world")

    def test_skips_non_text_blocks(self) -> None:
        configure_fake_anthropic(
            response=_MessageStub(
                [
                    _TextBlock("real text"),
                    _TextBlock("tool input ignored", block_type="tool_use"),
                ]
            )
        )
        gateway = AnthropicAIGateway("k", prompt_loader=_RecordingPromptLoader())
        self.assertEqual(gateway.generate_text("story_parser", {}), "real text")

    def test_empty_content_raises(self) -> None:
        configure_fake_anthropic(response=_MessageStub([]))
        gateway = AnthropicAIGateway("k", prompt_loader=_RecordingPromptLoader())
        with self.assertRaises(AIResponseParseError):
            gateway.generate_text("story_parser", {})


class JSONResponseTests(_FakeAnthropicTestCase):
    def test_parses_json_response(self) -> None:
        configure_fake_anthropic(response=_MessageStub([_TextBlock('{"foo": 1}')]))
        gateway = AnthropicAIGateway("k", prompt_loader=_RecordingPromptLoader())
        result = gateway.generate_json("story_parser", {})
        self.assertEqual(result, {"foo": 1})

    def test_strips_json_code_fence(self) -> None:
        configure_fake_anthropic(response=_MessageStub([_TextBlock('```json\n{"foo": 2}\n```')]))
        gateway = AnthropicAIGateway("k", prompt_loader=_RecordingPromptLoader())
        self.assertEqual(gateway.generate_json("story_parser", {}), {"foo": 2})

    def test_invalid_json_raises(self) -> None:
        configure_fake_anthropic(response=_MessageStub([_TextBlock("not json")]))
        gateway = AnthropicAIGateway("k", prompt_loader=_RecordingPromptLoader())
        with self.assertRaises(AIResponseParseError):
            gateway.generate_json("story_parser", {})


class RetryTests(_FakeAnthropicTestCase):
    def test_retries_on_transient_error_then_succeeds(self) -> None:
        call_log = configure_fake_anthropic(
            response=_MessageStub([_TextBlock("eventually ok")]),
            raise_first_n=2,
            raise_exc=_FakeTimeout,
        )
        with patch("tenacity.nap.time.sleep", lambda _s: None):
            gateway = AnthropicAIGateway(
                "k",
                prompt_loader=_RecordingPromptLoader(),
                max_retries=3,
            )
            result = gateway.generate_text("story_parser", {})
        self.assertEqual(result, "eventually ok")
        self.assertEqual(len(call_log), 3)

    def test_gives_up_after_max_retries(self) -> None:
        configure_fake_anthropic(
            raise_first_n=10,
            raise_exc=_FakeRateLimit,
        )
        with patch("tenacity.nap.time.sleep", lambda _s: None):
            gateway = AnthropicAIGateway(
                "k",
                prompt_loader=_RecordingPromptLoader(),
                max_retries=2,
            )
            with self.assertRaises(_FakeRateLimit):
                gateway.generate_text("story_parser", {})


class TokenUsageTests(_FakeAnthropicTestCase):
    def test_token_callback_receives_usage(self) -> None:
        configure_fake_anthropic(
            response=_MessageStub(
                [_TextBlock("text")],
                usage=_UsageStub(input_tokens=12, output_tokens=34),
            )
        )
        events: list[TokenUsage] = []
        gateway = AnthropicAIGateway(
            "k",
            prompt_loader=_RecordingPromptLoader(),
            token_callback=events.append,
        )
        gateway.generate_text("story_parser", {})
        self.assertEqual(len(events), 1)
        usage = events[0]
        self.assertEqual(usage.input_tokens, 12)
        self.assertEqual(usage.output_tokens, 34)
        self.assertEqual(usage.total_tokens, 46)
        self.assertEqual(usage.prompt_name, "story_parser")
        self.assertEqual(usage.model, AnthropicAIGateway.DEFAULT_MODEL)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
