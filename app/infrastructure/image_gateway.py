"""Image gateway contract for the render-orchestration layer (P2.4).

This is the image-side analogue of :mod:`app.infrastructure.ai_gateway`. The
core app produces ``Beat.image_prompt`` / ``Beat.negative_prompt`` deterministically;
an ``ImageGateway`` implementation is what turns those prompts into actual image
bytes by talking to an external renderer (ComfyUI, Stable Diffusion WebUI, a
hosted SDXL API, etc.).

The protocol is intentionally tiny so:

* Services depend on the protocol, not on any concrete renderer.
* Tests can supply a fake gateway without touching the network.
* New backends can be added without changing service code.

Returning raw ``bytes`` (rather than, say, a file path) keeps the boundary
clean: the gateway is only responsible for producing pixels; the calling
service (e.g. :class:`app.services.image_generation_service.ImageGenerationService`)
decides where to write them on disk and how to record them on the Beat.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ImageGateway(Protocol):
    """Render one image from a positive + negative prompt.

    Implementations must:

    * Be deterministic for the same ``seed`` (when the underlying model is).
    * Raise on configuration errors (bad host, missing model, etc.) rather than
      silently returning empty bytes.
    * Never persist the result themselves — return bytes and let the caller
      decide where to save them.

    A ``seed`` of ``None`` lets the implementation pick one (typically random).
    Callers that want reproducibility should always pass an explicit seed.
    """

    def generate(
        self,
        prompt: str,
        negative_prompt: str,
        *,
        seed: int | None = None,
    ) -> bytes:
        """Render the prompt and return the resulting image as raw bytes."""
