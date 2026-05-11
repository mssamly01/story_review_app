"""Tests for ComfyUIImageGateway (P2.4).

We patch :func:`urllib.request.urlopen` so the suite never hits a real ComfyUI
server. The fake responds to three endpoints:

* ``POST /prompt``                -> ``{"prompt_id": "..."}``
* ``GET  /history/{prompt_id}``   -> execution history with image metadata
* ``GET  /view?...``              -> raw PNG bytes

This gives us full coverage of the queue → poll → download flow without any
network or filesystem dependency.
"""

from __future__ import annotations

import io
import json
import unittest
from typing import Any
from unittest.mock import patch
from urllib import error as urllib_error

from app.infrastructure._ai_gateway_helpers import AIConfigurationError
from app.infrastructure.comfyui_image_gateway import (
    DEFAULT_WORKFLOW,
    ComfyUIHTTPError,
    ComfyUIImageGateway,
    ComfyUIRenderError,
)


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: Any) -> None:
        return None


class _FakeComfyUI:
    """In-memory ComfyUI substitute keyed on URL prefix.

    ``script`` is a per-endpoint queue of responses; once a request matches a
    prefix, the next entry from that queue is consumed. Entries can be raw
    bytes, a dict (JSON-encoded), or an exception instance to raise.
    """

    def __init__(self, script: dict[str, list[Any]]) -> None:
        self.script = {key: list(values) for key, values in script.items()}
        self.calls: list[dict[str, Any]] = []

    def urlopen(self, req: Any, timeout: float | None = None) -> _FakeResponse:
        url = req.full_url
        method = getattr(req, "method", None) or ("POST" if req.data else "GET")
        data: dict[str, Any] | None = None
        if req.data:
            try:
                data = json.loads(req.data.decode("utf-8"))
            except json.JSONDecodeError:
                data = None
        self.calls.append({"url": url, "method": method, "data": data, "timeout": timeout})

        for prefix, queue in self.script.items():
            if url.startswith(prefix):
                if not queue:
                    raise AssertionError(f"No scripted response left for {prefix!r}")
                entry = queue.pop(0)
                if isinstance(entry, BaseException):
                    raise entry
                if isinstance(entry, bytes):
                    return _FakeResponse(entry)
                return _FakeResponse(json.dumps(entry).encode("utf-8"))

        raise AssertionError(f"Unhandled URL in fake ComfyUI: {url!r}")


def _make_history_done(prompt_id: str, filename: str = "render.png") -> dict[str, Any]:
    return {
        prompt_id: {
            "status": {"status_str": "success", "completed": True},
            "outputs": {
                "9": {
                    "images": [
                        {
                            "filename": filename,
                            "subfolder": "",
                            "type": "output",
                        }
                    ]
                }
            },
        }
    }


def _make_history_running(prompt_id: str) -> dict[str, Any]:
    return {prompt_id: {"status": {"status_str": "running"}, "outputs": {}}}


class ConstructorTests(unittest.TestCase):
    def test_default_host_and_workflow(self) -> None:
        gateway = ComfyUIImageGateway()
        self.assertEqual(gateway.host, ComfyUIImageGateway.DEFAULT_HOST)
        self.assertEqual(gateway.workflow_template, DEFAULT_WORKFLOW)
        # Workflow is deep-copied so callers cannot mutate the module default.
        gateway.workflow_template["6"]["inputs"]["text"] = "mutated"
        self.assertEqual(DEFAULT_WORKFLOW["6"]["inputs"]["text"], "")

    def test_trailing_slash_stripped_from_host(self) -> None:
        gateway = ComfyUIImageGateway(host="http://comfy:8188/")
        self.assertEqual(gateway.host, "http://comfy:8188")

    def test_env_host_used_when_no_arg(self) -> None:
        with patch.dict("os.environ", {"COMFYUI_HOST": "http://envhost:9999"}, clear=False):
            gateway = ComfyUIImageGateway()
        self.assertEqual(gateway.host, "http://envhost:9999")


class WorkflowPreparationTests(unittest.TestCase):
    def test_prompt_negative_and_seed_are_substituted(self) -> None:
        gateway = ComfyUIImageGateway()
        wf = gateway._prepare_workflow("hero pose", "blurry", 4242)
        self.assertEqual(wf["6"]["inputs"]["text"], "hero pose")
        self.assertEqual(wf["7"]["inputs"]["text"], "blurry")
        self.assertEqual(wf["3"]["inputs"]["seed"], 4242)
        # Module-level default is untouched.
        self.assertEqual(DEFAULT_WORKFLOW["6"]["inputs"]["text"], "")
        self.assertEqual(DEFAULT_WORKFLOW["3"]["inputs"]["seed"], 0)

    def test_missing_positive_node_raises_configuration_error(self) -> None:
        gateway = ComfyUIImageGateway(workflow_template={"foo": {"inputs": {}}})
        with self.assertRaises(AIConfigurationError):
            gateway._prepare_workflow("p", "n", 1)


class HappyPathTests(unittest.TestCase):
    def test_queue_poll_download_returns_image_bytes(self) -> None:
        fake = _FakeComfyUI(
            {
                "http://h:1/prompt": [{"prompt_id": "p-001"}],
                "http://h:1/history/p-001": [_make_history_done("p-001")],
                "http://h:1/view": [b"PNGDATA"],
            }
        )
        gateway = ComfyUIImageGateway(
            host="http://h:1",
            poll_interval=0.0,
        )
        with patch(
            "app.infrastructure.comfyui_image_gateway.urllib_request.urlopen",
            fake.urlopen,
        ):
            result = gateway.generate("hero", "blurry", seed=42)

        self.assertEqual(result, b"PNGDATA")
        # Order of calls: prompt -> history -> view
        self.assertEqual(fake.calls[0]["method"], "POST")
        self.assertEqual(fake.calls[0]["url"], "http://h:1/prompt")
        self.assertEqual(fake.calls[0]["data"]["prompt"]["6"]["inputs"]["text"], "hero")
        self.assertEqual(fake.calls[0]["data"]["prompt"]["7"]["inputs"]["text"], "blurry")
        self.assertEqual(fake.calls[0]["data"]["prompt"]["3"]["inputs"]["seed"], 42)
        self.assertIn("client_id", fake.calls[0]["data"])
        self.assertEqual(fake.calls[1]["method"], "GET")
        self.assertEqual(fake.calls[1]["url"], "http://h:1/history/p-001")
        self.assertEqual(fake.calls[2]["method"], "GET")
        self.assertTrue(fake.calls[2]["url"].startswith("http://h:1/view?"))
        self.assertIn("filename=render.png", fake.calls[2]["url"])
        self.assertIn("type=output", fake.calls[2]["url"])

    def test_polls_until_image_is_ready(self) -> None:
        fake = _FakeComfyUI(
            {
                "http://h:1/prompt": [{"prompt_id": "p-9"}],
                "http://h:1/history/p-9": [
                    _make_history_running("p-9"),
                    _make_history_running("p-9"),
                    _make_history_done("p-9", filename="out.png"),
                ],
                "http://h:1/view": [b"BYTES"],
            }
        )
        gateway = ComfyUIImageGateway(host="http://h:1", poll_interval=0.0)
        with patch(
            "app.infrastructure.comfyui_image_gateway.urllib_request.urlopen",
            fake.urlopen,
        ):
            result = gateway.generate("p", "n", seed=1)
        self.assertEqual(result, b"BYTES")
        # 1 POST + 3 GET history + 1 GET view = 5 calls
        history_calls = [c for c in fake.calls if c["url"].startswith("http://h:1/history")]
        self.assertEqual(len(history_calls), 3)

    def test_seed_none_uses_seed_provider(self) -> None:
        fake = _FakeComfyUI(
            {
                "http://h:1/prompt": [{"prompt_id": "p-1"}],
                "http://h:1/history/p-1": [_make_history_done("p-1")],
                "http://h:1/view": [b"OK"],
            }
        )
        gateway = ComfyUIImageGateway(
            host="http://h:1",
            poll_interval=0.0,
            seed_provider=lambda: 1234567,
        )
        with patch(
            "app.infrastructure.comfyui_image_gateway.urllib_request.urlopen",
            fake.urlopen,
        ):
            gateway.generate("p", "n")
        self.assertEqual(fake.calls[0]["data"]["prompt"]["3"]["inputs"]["seed"], 1234567)


class ErrorPathTests(unittest.TestCase):
    def test_4xx_response_raises_configuration_error_without_retry(self) -> None:
        http_error = urllib_error.HTTPError(
            url="http://h:1/prompt",
            code=400,
            msg="bad request",
            hdrs=None,  # type: ignore[arg-type]
            fp=io.BytesIO(b"workflow invalid"),
        )
        fake = _FakeComfyUI({"http://h:1/prompt": [http_error]})
        gateway = ComfyUIImageGateway(host="http://h:1", poll_interval=0.0)
        with patch(
            "app.infrastructure.comfyui_image_gateway.urllib_request.urlopen",
            fake.urlopen,
        ):
            with self.assertRaises(AIConfigurationError):
                gateway.generate("p", "n", seed=1)
        self.assertEqual(len(fake.calls), 1, "4xx should not be retried")

    def test_5xx_response_is_retried_then_succeeds(self) -> None:
        http_error = urllib_error.HTTPError(
            url="http://h:1/prompt",
            code=503,
            msg="busy",
            hdrs=None,  # type: ignore[arg-type]
            fp=io.BytesIO(b"server busy"),
        )
        fake = _FakeComfyUI(
            {
                "http://h:1/prompt": [http_error, http_error, {"prompt_id": "p-r"}],
                "http://h:1/history/p-r": [_make_history_done("p-r")],
                "http://h:1/view": [b"AFTER_RETRY"],
            }
        )
        gateway = ComfyUIImageGateway(host="http://h:1", poll_interval=0.0)
        with patch("tenacity.nap.time.sleep", lambda *_: None):
            with patch(
                "app.infrastructure.comfyui_image_gateway.urllib_request.urlopen",
                fake.urlopen,
            ):
                result = gateway.generate("p", "n", seed=1)
        self.assertEqual(result, b"AFTER_RETRY")
        prompt_calls = [c for c in fake.calls if c["url"] == "http://h:1/prompt"]
        self.assertEqual(len(prompt_calls), 3)

    def test_render_error_when_workflow_reports_failure(self) -> None:
        history_failed = {
            "p-f": {
                "status": {
                    "status_str": "error",
                    "messages": [["execution_error", {"node_id": "3"}]],
                },
                "outputs": {},
            }
        }
        fake = _FakeComfyUI(
            {
                "http://h:1/prompt": [{"prompt_id": "p-f"}],
                "http://h:1/history/p-f": [history_failed],
            }
        )
        gateway = ComfyUIImageGateway(host="http://h:1", poll_interval=0.0)
        with patch(
            "app.infrastructure.comfyui_image_gateway.urllib_request.urlopen",
            fake.urlopen,
        ):
            with self.assertRaises(ComfyUIRenderError):
                gateway.generate("p", "n", seed=1)

    def test_render_error_when_polling_times_out(self) -> None:
        fake = _FakeComfyUI(
            {
                "http://h:1/prompt": [{"prompt_id": "p-t"}],
                "http://h:1/history/p-t": [
                    _make_history_running("p-t"),
                    _make_history_running("p-t"),
                ],
            }
        )
        gateway = ComfyUIImageGateway(
            host="http://h:1",
            poll_interval=0.0,
            max_poll_attempts=2,
        )
        with patch(
            "app.infrastructure.comfyui_image_gateway.urllib_request.urlopen",
            fake.urlopen,
        ):
            with self.assertRaises(ComfyUIRenderError):
                gateway.generate("p", "n", seed=1)

    def test_render_error_when_no_prompt_id_returned(self) -> None:
        fake = _FakeComfyUI({"http://h:1/prompt": [{"error": "nope"}]})
        gateway = ComfyUIImageGateway(host="http://h:1", poll_interval=0.0)
        with patch(
            "app.infrastructure.comfyui_image_gateway.urllib_request.urlopen",
            fake.urlopen,
        ):
            with self.assertRaises(ComfyUIRenderError):
                gateway.generate("p", "n", seed=1)

    def test_render_error_when_view_returns_empty_body(self) -> None:
        fake = _FakeComfyUI(
            {
                "http://h:1/prompt": [{"prompt_id": "p-e"}],
                "http://h:1/history/p-e": [_make_history_done("p-e")],
                "http://h:1/view": [b""],
            }
        )
        gateway = ComfyUIImageGateway(host="http://h:1", poll_interval=0.0)
        with patch(
            "app.infrastructure.comfyui_image_gateway.urllib_request.urlopen",
            fake.urlopen,
        ):
            with self.assertRaises(ComfyUIRenderError):
                gateway.generate("p", "n", seed=1)


class HTTPErrorTypeTests(unittest.TestCase):
    def test_comfyui_http_error_message_includes_status(self) -> None:
        err = ComfyUIHTTPError(503, "server busy")
        self.assertIn("503", str(err))
        self.assertIn("server busy", str(err))
        self.assertEqual(err.status_code, 503)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
