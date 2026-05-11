"""HTTP-backed image gateway that talks to a ComfyUI server (P2.4).

ComfyUI is an open-source local image-generation server with a graph-based
workflow runtime. It exposes a small REST surface:

* ``POST /prompt``                 — queue a workflow, returns ``{"prompt_id": ...}``.
* ``GET  /history/{prompt_id}``    — poll for execution result; the response
  contains an ``outputs`` block keyed by node id with ``images`` metadata.
* ``GET  /view?filename=...``      — download the actual PNG bytes.

This gateway implements the three-step flow above and exposes the result as a
single ``generate(prompt, negative_prompt, seed=None) -> bytes`` call matching
:class:`app.infrastructure.image_gateway.ImageGateway`.

All HTTP traffic goes through :mod:`urllib`, so the gateway adds no new
runtime dependency. Transient errors (network drops, 5xx responses, timeouts)
are retried with exponential backoff via :mod:`tenacity` when available, and
fall back to a single no-retry call otherwise — mirroring the resilience
pattern used by the AI gateways.
"""

from __future__ import annotations

import copy
import json
import logging
import os
import random
import time
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from app.infrastructure._ai_gateway_helpers import AIConfigurationError
from app.infrastructure.image_gateway import ImageGateway

logger = logging.getLogger(__name__)

__all__ = [
    "ComfyUIImageGateway",
    "ComfyUIHTTPError",
    "ComfyUIRenderError",
    "DEFAULT_WORKFLOW",
]


class ComfyUIHTTPError(RuntimeError):
    """Raised when ComfyUI returns a non-2xx response."""

    def __init__(self, status_code: int, body: str) -> None:
        super().__init__(f"ComfyUI HTTP {status_code}: {body[:200]}")
        self.status_code = status_code
        self.body = body


class ComfyUIRenderError(RuntimeError):
    """Raised when ComfyUI accepts the workflow but never produces an image.

    Common causes: timed out polling, the workflow failed inside the server,
    or the output node didn't actually emit an image. The caller should treat
    this as a render failure rather than a network glitch.
    """


# A minimal but valid txt2img workflow. Real callers will typically pass their
# own workflow exported from ComfyUI's UI; this default exists so the gateway
# is usable out-of-the-box for smoke tests and unit tests that only need the
# HTTP shape (not a real render). Node ids match ComfyUI's default template:
#
#   "3" = KSampler (positive seed input lives here)
#   "6" = CLIPTextEncode (positive prompt)
#   "7" = CLIPTextEncode (negative prompt)
DEFAULT_WORKFLOW: dict[str, Any] = {
    "3": {
        "inputs": {
            "seed": 0,
            "steps": 20,
            "cfg": 7.0,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 1.0,
            "model": ["4", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0],
        },
        "class_type": "KSampler",
    },
    "4": {
        "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
        "class_type": "CheckpointLoaderSimple",
    },
    "5": {
        "inputs": {"width": 1024, "height": 1024, "batch_size": 1},
        "class_type": "EmptyLatentImage",
    },
    "6": {
        "inputs": {"text": "", "clip": ["4", 1]},
        "class_type": "CLIPTextEncode",
    },
    "7": {
        "inputs": {"text": "", "clip": ["4", 1]},
        "class_type": "CLIPTextEncode",
    },
    "8": {
        "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        "class_type": "VAEDecode",
    },
    "9": {
        "inputs": {"filename_prefix": "story_review", "images": ["8", 0]},
        "class_type": "SaveImage",
    },
}


def _resolve_retryable_exceptions() -> tuple[type[BaseException], ...]:
    """Transient network errors plus 5xx responses are worth retrying."""
    return (
        urllib_error.URLError,
        TimeoutError,
        ConnectionError,
        ComfyUIHTTPError,
    )


class ComfyUIImageGateway(ImageGateway):
    DEFAULT_HOST = "http://localhost:8188"
    DEFAULT_TIMEOUT_SECONDS = 60.0
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_POLL_INTERVAL_SECONDS = 1.0
    # ~3 minutes worst case at the default 1s poll. Long-running workflows
    # should bump this rather than ratchet the poll interval down.
    DEFAULT_MAX_POLL_ATTEMPTS = 180

    # Which node ids inside the workflow carry the positive prompt, negative
    # prompt, and KSampler seed. Defaults match the workflow in
    # :data:`DEFAULT_WORKFLOW` and ComfyUI's stock txt2img template.
    DEFAULT_POSITIVE_PROMPT_NODE = "6"
    DEFAULT_NEGATIVE_PROMPT_NODE = "7"
    DEFAULT_SEED_NODE = "3"

    MAX_SEED = 2**32 - 1

    def __init__(
        self,
        host: str | None = None,
        workflow_template: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        poll_interval: float | None = None,
        max_poll_attempts: int | None = None,
        client_id: str | None = None,
        positive_prompt_node: str | None = None,
        negative_prompt_node: str | None = None,
        seed_node: str | None = None,
        seed_provider: Any = None,
    ) -> None:
        self.host = (host or os.environ.get("COMFYUI_HOST") or self.DEFAULT_HOST).rstrip("/")
        self.workflow_template = copy.deepcopy(workflow_template or DEFAULT_WORKFLOW)
        self.timeout = float(timeout) if timeout is not None else self.DEFAULT_TIMEOUT_SECONDS
        self.max_retries = int(max_retries) if max_retries is not None else self.DEFAULT_MAX_RETRIES
        self.poll_interval = (
            float(poll_interval)
            if poll_interval is not None
            else self.DEFAULT_POLL_INTERVAL_SECONDS
        )
        self.max_poll_attempts = (
            int(max_poll_attempts)
            if max_poll_attempts is not None
            else self.DEFAULT_MAX_POLL_ATTEMPTS
        )
        self.client_id = client_id or f"story_review_{random.randint(0, 1 << 31)}"
        self.positive_prompt_node = positive_prompt_node or self.DEFAULT_POSITIVE_PROMPT_NODE
        self.negative_prompt_node = negative_prompt_node or self.DEFAULT_NEGATIVE_PROMPT_NODE
        self.seed_node = seed_node or self.DEFAULT_SEED_NODE
        self._seed_provider = seed_provider or (
            lambda: random.SystemRandom().randint(0, self.MAX_SEED)
        )

    # ----- public protocol -----

    def generate(
        self,
        prompt: str,
        negative_prompt: str,
        *,
        seed: int | None = None,
    ) -> bytes:
        """Render the prompt and return the rendered PNG bytes."""
        resolved_seed = int(seed) if seed is not None else int(self._seed_provider())
        workflow = self._prepare_workflow(prompt, negative_prompt, resolved_seed)
        prompt_id = self._queue_prompt(workflow)
        image_meta = self._wait_for_image(prompt_id)
        return self._download_image(image_meta)

    # ----- workflow assembly -----

    def _prepare_workflow(
        self,
        prompt: str,
        negative_prompt: str,
        seed: int,
    ) -> dict[str, Any]:
        workflow = copy.deepcopy(self.workflow_template)

        positive_node = workflow.get(self.positive_prompt_node)
        if not isinstance(positive_node, dict) or "inputs" not in positive_node:
            raise AIConfigurationError(
                f"Workflow template missing positive prompt node " f"{self.positive_prompt_node!r}."
            )
        positive_node["inputs"]["text"] = prompt

        negative_node = workflow.get(self.negative_prompt_node)
        if not isinstance(negative_node, dict) or "inputs" not in negative_node:
            raise AIConfigurationError(
                f"Workflow template missing negative prompt node " f"{self.negative_prompt_node!r}."
            )
        negative_node["inputs"]["text"] = negative_prompt

        seed_node = workflow.get(self.seed_node)
        if not isinstance(seed_node, dict) or "inputs" not in seed_node:
            raise AIConfigurationError(f"Workflow template missing seed node {self.seed_node!r}.")
        seed_node["inputs"]["seed"] = seed
        return workflow

    # ----- queue + poll + download -----

    def _queue_prompt(self, workflow: dict[str, Any]) -> str:
        payload = {"prompt": workflow, "client_id": self.client_id}
        response = self._post_json_with_retry(f"{self.host}/prompt", payload)
        prompt_id = response.get("prompt_id")
        if not isinstance(prompt_id, str) or not prompt_id:
            raise ComfyUIRenderError(f"ComfyUI did not return a prompt_id; got: {response!r}")
        return prompt_id

    def _wait_for_image(self, prompt_id: str) -> dict[str, Any]:
        history_url = f"{self.host}/history/{urllib_parse.quote(prompt_id, safe='')}"
        last_history: dict[str, Any] | None = None
        for _ in range(self.max_poll_attempts):
            history = self._get_json_with_retry(history_url)
            entry = history.get(prompt_id) if isinstance(history, dict) else None
            if isinstance(entry, dict):
                last_history = entry
                image_meta = self._extract_first_image(entry)
                if image_meta is not None:
                    return image_meta
                status = entry.get("status")
                if isinstance(status, dict) and status.get("status_str") == "error":
                    messages = status.get("messages", [])
                    raise ComfyUIRenderError(f"ComfyUI workflow {prompt_id} failed: {messages!r}")
            time.sleep(self.poll_interval)
        raise ComfyUIRenderError(
            f"Timed out waiting for ComfyUI prompt {prompt_id} to finish; "
            f"last history payload: {last_history!r}"
        )

    @staticmethod
    def _extract_first_image(history_entry: dict[str, Any]) -> dict[str, Any] | None:
        outputs = history_entry.get("outputs")
        if not isinstance(outputs, dict):
            return None
        for node_output in outputs.values():
            if not isinstance(node_output, dict):
                continue
            images = node_output.get("images")
            if not isinstance(images, list):
                continue
            for image in images:
                if isinstance(image, dict) and image.get("filename"):
                    return image
        return None

    def _download_image(self, image_meta: dict[str, Any]) -> bytes:
        params = {
            "filename": str(image_meta.get("filename", "")),
            "subfolder": str(image_meta.get("subfolder", "")),
            "type": str(image_meta.get("type", "output")),
        }
        url = f"{self.host}/view?{urllib_parse.urlencode(params)}"
        data = self._get_bytes_with_retry(url)
        if not data:
            raise ComfyUIRenderError(f"ComfyUI returned empty image bytes for {params!r}.")
        return data

    # ----- HTTP plumbing -----

    def _post_json_with_retry(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._run_with_retry(lambda: self._post_json(url, payload))

    def _get_json_with_retry(self, url: str) -> dict[str, Any]:
        return self._run_with_retry(lambda: self._get_json(url))

    def _get_bytes_with_retry(self, url: str) -> bytes:
        return self._run_with_retry(lambda: self._get_bytes(url))

    def _run_with_retry(self, call: Any) -> Any:
        try:
            from tenacity import (
                retry,
                retry_if_exception_type,
                stop_after_attempt,
                wait_exponential,
            )
        except ImportError:
            logger.warning(
                "tenacity not installed; ComfyUI gateway will not retry on "
                "transient errors. Install requirements-ai.txt for retry support."
            )
            return call()

        retryable = _resolve_retryable_exceptions()
        attempts = max(1, self.max_retries)

        @retry(
            reraise=True,
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(retryable),
        )
        def _do_call() -> Any:
            return call()

        return _do_call()

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = urllib_request.Request(  # noqa: S310 - configurable host
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        raw = self._urlopen_read(req)
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ComfyUIRenderError("ComfyUI response body was not valid JSON.") from exc
        if not isinstance(data, dict):
            raise ComfyUIRenderError("ComfyUI response root was not a JSON object.")
        return data

    def _get_json(self, url: str) -> dict[str, Any]:
        req = urllib_request.Request(url, method="GET")  # noqa: S310
        raw = self._urlopen_read(req)
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ComfyUIRenderError("ComfyUI response body was not valid JSON.") from exc
        if not isinstance(data, dict):
            raise ComfyUIRenderError("ComfyUI response root was not a JSON object.")
        return data

    def _get_bytes(self, url: str) -> bytes:
        req = urllib_request.Request(url, method="GET")  # noqa: S310
        return self._urlopen_read(req)

    def _urlopen_read(self, req: urllib_request.Request) -> bytes:
        try:
            with urllib_request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                return resp.read()
        except urllib_error.HTTPError as exc:
            body_text = ""
            try:
                body_text = exc.read().decode("utf-8", errors="replace")
            except Exception:  # pragma: no cover - defensive
                pass
            if 500 <= exc.code < 600:
                raise ComfyUIHTTPError(exc.code, body_text) from exc
            raise AIConfigurationError(
                f"ComfyUI returned HTTP {exc.code}: {body_text[:200]}"
            ) from exc
