"""Narrative beat domain model.

A beat is the smallest production unit in the app: one narratable moment and
one image-promptable visual idea.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
        )
