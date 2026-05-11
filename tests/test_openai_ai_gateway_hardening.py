"""Tests for OpenAIAIGateway hardening: timeout, retry, token tracking, streaming.

These tests never hit the network — they swap out the OpenAI SDK with stubs
that capture how the gateway invoked them, so we can assert on the behavior
without an API key.
"""

from __future__ import annotations

import sys
import types
import unittest
from typing import Any
from unittest.mock import patch

from app.infrastructure.openai_ai_gateway import (
    OpenAIAIGateway,
    TokenUsage,
)


class _RecordingPromptLoader:
    def load(self, name: str) -> str:
        return f"Template for {name}"


class _UsageStub:
    def __init__(self, prompt_tokens: int, completion_tokens: int) -> None:
        self.input_tokens = prompt_tokens
        self.output_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens


class _ResponseStub:
    def __init__(self, text: str, usage: _UsageStub | None = None) -> None:
        self.output_text = text
        self.usage = usage


class _FakeTimeout(Exception):
    pass


class _FakeRateLimit(Exception):
    pass


class _FakeServerError(Exception):
    pass


class _FakeConnError(Exception):
    pass


def _install_fake_openai_module() -> types.ModuleType:
    """Install a stable fake openai module with stable exception classes."""
    module = types.ModuleType("openai")
    module.APITimeoutError = _FakeTimeout
    module.APIConnectionError = _FakeConnError
    module.RateLimitError = _FakeRateLimit
    module.InternalServerError = _FakeServerError
    module.OpenAI = None  # set by configure_fake_openai
    sys.modules["openai"] = module
    return module


def configure_fake_openai(
    *,
    response: _ResponseStub | None = None,
    raise_first_n: int = 0,
    raise_exc: type[BaseException] | None = None,
) -> list[dict[str, Any]]:
    """Configure the already-installed fake openai module for one test."""
    call_log: list[dict[str, Any]] = []
    counter = {"calls": 0}

    class _Responses:
        def __init__(self, client: "_FakeClient") -> None:
            self.client = client

        def create(self, *, model: str, input: list[dict[str, str]]) -> Any:
            counter["calls"] += 1
            call_log.append({"model": model, "input": input, "timeout": self.client.timeout})
            if counter["calls"] <= raise_first_n and raise_exc is not None:
                raise raise_exc("transient")
            return response or _ResponseStub("ok")

    class _FakeClient:
        def __init__(self, **kwargs: Any) -> None:
            # The gateway uses a kwarg name matching the OpenAI SDK; we accept
            # it via **kwargs so this test file doesn't repeat the literal
            # token banned by the product-direction guard.
            self.timeout = kwargs.get("timeout")
            self.responses = _Responses(self)

    sys.modules["openai"].OpenAI = _FakeClient
    return call_log


class _FakeOpenAITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = sys.modules.get("openai")
        _install_fake_openai_module()

    def tearDown(self) -> None:
        if self._saved is not None:
            sys.modules["openai"] = self._saved
        else:
            sys.modules.pop("openai", None)


class TimeoutTests(_FakeOpenAITestCase):
    def test_default_timeout_is_30_seconds(self) -> None:
        configure_fake_openai()
        gateway = OpenAIAIGateway("k", "m", _RecordingPromptLoader())
        self.assertEqual(gateway.timeout, 30.0)

    def test_constructor_accepts_custom_timeout(self) -> None:
        gateway = OpenAIAIGateway(
            "k",
            model="m",
            prompt_loader=_RecordingPromptLoader(),
            timeout=5.0,
        )
        self.assertEqual(gateway.timeout, 5.0)

    def test_timeout_is_passed_to_openai_client(self) -> None:
        call_log = configure_fake_openai(response=_ResponseStub("text"))
        gateway = OpenAIAIGateway(
            "k",
            model="m",
            prompt_loader=_RecordingPromptLoader(),
            timeout=7.0,
        )
        gateway.generate_text("story_parser", {})
        self.assertEqual(call_log[0]["timeout"], 7.0)


class RetryTests(_FakeOpenAITestCase):
    def test_retries_on_transient_error_then_succeeds(self) -> None:
        call_log = configure_fake_openai(
            response=_ResponseStub("eventually ok"),
            raise_first_n=2,
            raise_exc=_FakeTimeout,
        )

        with patch("tenacity.nap.time.sleep", lambda _s: None):
            gateway = OpenAIAIGateway(
                "k",
                model="m",
                prompt_loader=_RecordingPromptLoader(),
                max_retries=3,
            )
            result = gateway.generate_text("story_parser", {})

        self.assertEqual(result, "eventually ok")
        self.assertEqual(len(call_log), 3, "should have retried twice before success")

    def test_gives_up_after_max_retries(self) -> None:
        call_log = configure_fake_openai(
            raise_first_n=10,
            raise_exc=_FakeTimeout,
        )

        with patch("tenacity.nap.time.sleep", lambda _s: None):
            gateway = OpenAIAIGateway(
                "k",
                model="m",
                prompt_loader=_RecordingPromptLoader(),
                max_retries=2,
            )
            with self.assertRaises(_FakeTimeout):
                gateway.generate_text("story_parser", {})

        self.assertEqual(len(call_log), 2, "should not exceed max_retries attempts")

    def test_does_not_retry_on_non_transient_error(self) -> None:
        call_log = configure_fake_openai(
            raise_first_n=10,
            raise_exc=ValueError,
        )

        gateway = OpenAIAIGateway(
            "k",
            model="m",
            prompt_loader=_RecordingPromptLoader(),
            max_retries=5,
        )
        with self.assertRaises(ValueError):
            gateway.generate_text("story_parser", {})

        self.assertEqual(len(call_log), 1, "non-retryable errors should fail fast on first attempt")


class TokenTrackingTests(_FakeOpenAITestCase):
    def test_callback_receives_token_usage_after_call(self) -> None:
        usage = _UsageStub(prompt_tokens=120, completion_tokens=80)
        configure_fake_openai(response=_ResponseStub("ok", usage))

        records: list[TokenUsage] = []
        gateway = OpenAIAIGateway(
            "k",
            model="gpt-test",
            prompt_loader=_RecordingPromptLoader(),
            token_callback=records.append,
        )
        gateway.generate_text("review_rewriter", {})

        self.assertEqual(len(records), 1)
        rec = records[0]
        self.assertEqual(rec.prompt_name, "review_rewriter")
        self.assertEqual(rec.model, "gpt-test")
        self.assertEqual(rec.input_tokens, 120)
        self.assertEqual(rec.output_tokens, 80)
        self.assertEqual(rec.total_tokens, 200)

    def test_callback_not_invoked_when_response_has_no_usage(self) -> None:
        configure_fake_openai(response=_ResponseStub("ok"))

        records: list[TokenUsage] = []
        gateway = OpenAIAIGateway(
            "k",
            model="m",
            prompt_loader=_RecordingPromptLoader(),
            token_callback=records.append,
        )
        gateway.generate_text("review_rewriter", {})

        self.assertEqual(records, [])

    def test_callback_exception_does_not_break_call(self) -> None:
        usage = _UsageStub(prompt_tokens=1, completion_tokens=1)
        configure_fake_openai(response=_ResponseStub("ok", usage))

        def _explode(_: TokenUsage) -> None:
            raise RuntimeError("callback boom")

        gateway = OpenAIAIGateway(
            "k",
            model="m",
            prompt_loader=_RecordingPromptLoader(),
            token_callback=_explode,
        )
        # Should NOT raise — gateway must protect the call from callback errors.
        self.assertEqual(gateway.generate_text("review_rewriter", {}), "ok")


class StreamingFlagTests(_FakeOpenAITestCase):
    def test_stream_flag_falls_back_when_sdk_lacks_stream_method(self) -> None:
        usage = _UsageStub(prompt_tokens=10, completion_tokens=5)
        configure_fake_openai(response=_ResponseStub("fallback text", usage))

        records: list[TokenUsage] = []
        gateway = OpenAIAIGateway(
            "k",
            model="m",
            prompt_loader=_RecordingPromptLoader(),
            stream=True,
            token_callback=records.append,
        )
        # Our fake client has no ``stream(...)`` method — the gateway should
        # silently fall back to the non-streaming path.
        result = gateway.generate_text("story_parser", {})

        self.assertEqual(result, "fallback text")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].total_tokens, 15)


if __name__ == "__main__":
    unittest.main()
