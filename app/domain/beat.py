"""Narrative beat domain model.

A beat is the smallest production unit in the app: one narratable moment and
one image-promptable visual idea. After the prompt is rendered externally
(Midjourney / Stable Diffusion / ComfyUI / DALL-E), one or more
``BeatImageVariant`` entries can be attached to the beat to close the feedback
loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domain.dialogue import Dialogue


@dataclass(slots=True)
class BeatImageVariant:
    """A single rendered image artifact attached to a Beat.

    The app never generates these — they are produced by an external image
    model and imported back via ``BeatImageService`` / ``story-review
    import-image``. Storing them on the Beat closes the feedback loop so a
    project knows which beats have visuals and which variant is selected.
    """

    image_id: str
    image_path: str
    model: str = ""
    seed: str = ""
    generated_at: str = ""
    selected: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_id": self.image_id,
            "image_path": self.image_path,
            "model": self.model,
            "seed": self.seed,
            "generated_at": self.generated_at,
            "selected": self.selected,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BeatImageVariant":
        return cls(
            image_id=str(data["image_id"]),
            image_path=str(data["image_path"]),
            model=str(data.get("model", "")),
            seed=str(data.get("seed", "")),
            generated_at=str(data.get("generated_at", "")),
            selected=bool(data.get("selected", False)),
            notes=str(data.get("notes", "")),
        )


@dataclass(slots=True)
class Beat:
    beat_id: str
    scene_id: str
    order_index: int
    story_function: str = ""
    characters: list[str] = field(default_factory=list)
    location: str = ""
    action: str = ""
    emotion: str = ""
    shot_type: str = ""
    review_text: str = ""
    visual_description: str = ""
    image_prompt: str = ""
    negative_prompt: str = ""
    continuity_tags: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)
    status: str = "planned"
    images: list[BeatImageVariant] = field(default_factory=list)
    dialogues: list[Dialogue] = field(default_factory=list)

    @property
    def selected_image(self) -> BeatImageVariant | None:
        for image in self.images:
            if image.selected:
                return image
        return None

    @property
    def image_path(self) -> str:
        """Convenience accessor for the selected image's local path."""
        selected = self.selected_image
        return selected.image_path if selected else ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "beat_id": self.beat_id,
            "scene_id": self.scene_id,
            "order_index": self.order_index,
            "source_refs": list(self.source_refs),
            "story_function": self.story_function,
            "characters": list(self.characters),
            "location": self.location,
            "action": self.action,
            "emotion": self.emotion,
            "shot_type": self.shot_type,
            "review_text": self.review_text,
            "visual_description": self.visual_description,
            "image_prompt": self.image_prompt,
            "negative_prompt": self.negative_prompt,
            "continuity_tags": list(self.continuity_tags),
            "status": self.status,
            "images": [image.to_dict() for image in self.images],
            "dialogues": [dialogue.to_dict() for dialogue in self.dialogues],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Beat":
        return cls(
            beat_id=data["beat_id"],
            scene_id=data["scene_id"],
            order_index=int(data.get("order_index", 0)),
            source_refs=list(data.get("source_refs", [])),
            story_function=data.get("story_function", ""),
            characters=list(data.get("characters", [])),
            location=data.get("location", ""),
            action=data.get("action", ""),
            emotion=data.get("emotion", ""),
            shot_type=data.get("shot_type", ""),
            review_text=data.get("review_text", ""),
            visual_description=data.get("visual_description", ""),
            image_prompt=data.get("image_prompt", ""),
            negative_prompt=data.get("negative_prompt", ""),
            continuity_tags=list(data.get("continuity_tags", [])),
            status=data.get("status", "planned"),
            images=[BeatImageVariant.from_dict(img) for img in data.get("images", [])],
            dialogues=[Dialogue.from_dict(d) for d in data.get("dialogues", [])],
        )
