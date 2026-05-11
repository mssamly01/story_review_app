"""Render a Beat's image prompt via an :class:`ImageGateway` (P2.4).

This service is the orchestration half of the optional B-direction (Novel-to-Comic
Full Generator). The A-direction flow (the default) is unchanged:

    Beat.image_prompt  ->  user copies into Midjourney/SD/ComfyUI manually
    Beat.images        <-  BeatImageService.attach_image(...)  (P1.3)

The B-direction flow uses this service to close the render loop inside the app:

    Beat.image_prompt  ->  ImageGenerationService.render_beat(...)
                              -> ImageGateway.generate(prompt, negative_prompt, seed)
                              -> bytes written to disk
                              -> BeatImageService.attach_image(...)
    Beat.images        <-  the resulting BeatImageVariant

The service intentionally delegates persistence to :class:`BeatImageService` so
both flows share the same domain semantics (selection rules, JSON shape,
``project.touch()`` bookkeeping).
"""

from __future__ import annotations

import datetime as _dt
import random
from pathlib import Path
from typing import Callable

from app.domain.beat import Beat, BeatImageVariant
from app.domain.project import Project
from app.infrastructure.image_gateway import ImageGateway
from app.services.beat_image_service import BeatImageService


class ImageGenerationService:
    """Render Beat image prompts through an ImageGateway and attach the result."""

    DEFAULT_MODEL_LABEL = "comfyui"
    MAX_SEED = 2**32 - 1

    def __init__(
        self,
        image_gateway: ImageGateway,
        beat_image_service: BeatImageService | None = None,
        *,
        output_dir: str | Path = "images",
        model_label: str | None = None,
        seed_provider: Callable[[], int] | None = None,
    ) -> None:
        self.image_gateway = image_gateway
        self.beat_image_service = beat_image_service or BeatImageService()
        self.output_dir = Path(output_dir)
        self.model_label = model_label or self.DEFAULT_MODEL_LABEL
        self._seed_provider = seed_provider or (
            lambda: random.SystemRandom().randint(0, self.MAX_SEED)
        )

    def render_beat(
        self,
        project: Project,
        beat_id: str,
        *,
        seed: int | None = None,
        select: bool = True,
    ) -> BeatImageVariant:
        """Render ``beat.image_prompt`` and attach the result as a variant.

        ``seed=None`` lets the service pick a random reproducible seed and
        record it on the variant; pass an explicit seed to re-render the same
        Beat deterministically.
        """
        beat = self._find_beat(project, beat_id)
        if not beat.image_prompt.strip():
            raise ValueError(
                f"Beat {beat_id!r} has no image_prompt to render. "
                "Run PromptBuilderService first."
            )

        resolved_seed = int(seed) if seed is not None else int(self._seed_provider())
        image_bytes = self.image_gateway.generate(
            beat.image_prompt,
            beat.negative_prompt,
            seed=resolved_seed,
        )
        if not image_bytes:
            raise ValueError(f"ImageGateway returned empty bytes for beat {beat_id!r}.")

        output_path = self._write_image_file(beat_id, resolved_seed, image_bytes)
        return self.beat_image_service.attach_image(
            project,
            beat_id,
            str(output_path),
            model=self.model_label,
            seed=str(resolved_seed),
            select=select,
        )

    # ----- helpers -----

    def _find_beat(self, project: Project, beat_id: str) -> Beat:
        for episode in project.review_episodes:
            for scene in episode.scenes:
                for beat in scene.beats:
                    if beat.beat_id == beat_id:
                        return beat
        raise LookupError(f"Beat not found: {beat_id!r}")

    def _write_image_file(self, beat_id: str, seed: int, image_bytes: bytes) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"{beat_id}_{timestamp}_{seed}.png"
        output_path = self.output_dir / filename
        output_path.write_bytes(image_bytes)
        return output_path
