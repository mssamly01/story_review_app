"""Service for attaching externally-rendered images back to beats.

This service does NOT generate images — that responsibility belongs to an
external tool (Midjourney, Stable Diffusion, ComfyUI, DALL-E, etc.). It only
imports the resulting image file path + metadata into the project so the
beat knows which prompt was actually rendered, which variant was picked,
and where the file lives on disk.

This is the closing half of the feedback loop:

    Beat.image_prompt  (out)  ->  external renderer
    Beat.images        (in)   <-  BeatImageService.attach_image(...)
"""

from __future__ import annotations

import datetime as _dt
import uuid

from app.domain.beat import Beat, BeatImageVariant
from app.domain.project import Project
from app.services.project_service import ProjectService


class BeatImageService:
    def __init__(self, project_service: ProjectService | None = None) -> None:
        self.project_service = project_service or ProjectService()

    def attach_image(
        self,
        project: Project,
        beat_id: str,
        image_path: str,
        *,
        model: str = "",
        seed: str = "",
        notes: str = "",
        select: bool = True,
    ) -> BeatImageVariant:
        beat = self._find_beat(project, beat_id)
        variant = BeatImageVariant(
            image_id=f"img_{uuid.uuid4().hex[:8]}",
            image_path=image_path,
            model=model,
            seed=seed,
            generated_at=_dt.datetime.now(_dt.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            selected=False,
            notes=notes,
        )
        beat.images.append(variant)
        if select:
            self._mark_selected(beat, variant.image_id)
        project.touch()
        return variant

    def select_image(self, project: Project, beat_id: str, image_id: str) -> BeatImageVariant:
        beat = self._find_beat(project, beat_id)
        variant = self._mark_selected(beat, image_id)
        project.touch()
        return variant

    def remove_image(self, project: Project, beat_id: str, image_id: str) -> None:
        beat = self._find_beat(project, beat_id)
        original_count = len(beat.images)
        beat.images = [img for img in beat.images if img.image_id != image_id]
        if len(beat.images) == original_count:
            raise LookupError(f"Image {image_id!r} not found on beat {beat_id!r}")
        project.touch()

    def list_images(self, project: Project, beat_id: str) -> list[BeatImageVariant]:
        return list(self._find_beat(project, beat_id).images)

    def _find_beat(self, project: Project, beat_id: str) -> Beat:
        for episode in project.review_episodes:
            for scene in episode.scenes:
                for beat in scene.beats:
                    if beat.beat_id == beat_id:
                        return beat
        raise LookupError(f"Beat not found: {beat_id!r}")

    def _mark_selected(self, beat: Beat, image_id: str) -> BeatImageVariant:
        target: BeatImageVariant | None = None
        for image in beat.images:
            if image.image_id == image_id:
                target = image
                break
        if target is None:
            raise LookupError(f"Image {image_id!r} not found on beat {beat.beat_id!r}")
        for image in beat.images:
            image.selected = image.image_id == image_id
        return target
