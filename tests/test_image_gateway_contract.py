"""Contract tests for the :class:`ImageGateway` protocol (P2.4).

These tests pin down the *shape* of the contract so future implementations
(ComfyUI, Stable Diffusion WebUI, hosted SDXL, etc.) all stay swappable. They
do not exercise any real renderer.
"""

from __future__ import annotations

import unittest

from app.infrastructure.image_gateway import ImageGateway


class _GoodGateway:
    """Reference implementation: returns deterministic bytes per seed."""

    def generate(
        self,
        prompt: str,
        negative_prompt: str,
        *,
        seed: int | None = None,
    ) -> bytes:
        # Encode the contract in the output so the test can verify the args
        # flowed through correctly.
        return f"{prompt}|{negative_prompt}|{seed}".encode("utf-8")


class _MissingSeedKwargGateway:
    """Wrong: drops the keyword-only ``seed`` argument."""

    def generate(self, prompt: str, negative_prompt: str) -> bytes:
        return b""


class ImageGatewayProtocolTests(unittest.TestCase):
    def test_good_implementation_passes_runtime_isinstance(self) -> None:
        self.assertIsInstance(_GoodGateway(), ImageGateway)

    def test_implementation_without_generate_method_fails(self) -> None:
        class _NoGenerate:
            pass

        self.assertNotIsInstance(_NoGenerate(), ImageGateway)

    def test_generate_returns_bytes(self) -> None:
        gateway: ImageGateway = _GoodGateway()
        result = gateway.generate("hero", "blurry", seed=42)
        self.assertIsInstance(result, bytes)
        self.assertEqual(result, b"hero|blurry|42")

    def test_generate_supports_none_seed(self) -> None:
        gateway: ImageGateway = _GoodGateway()
        result = gateway.generate("hero", "blurry")
        # Calling without seed must not raise and must still return bytes.
        self.assertEqual(result, b"hero|blurry|None")

    def test_missing_seed_kwarg_is_still_protocol_compatible_at_runtime(self) -> None:
        # Python's runtime Protocol check only verifies method names, not
        # signatures. That's expected — we document this so future contributors
        # don't add brittle signature introspection here.
        self.assertIsInstance(_MissingSeedKwargGateway(), ImageGateway)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
