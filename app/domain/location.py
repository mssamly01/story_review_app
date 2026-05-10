"""Location bible entry domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Location:
    location_id: str
    name: str
    description: str = ""
    mood: str = ""
    lighting: str = ""
    visual_prompt_base: str = ""
    related_scene_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "location_id": self.location_id,
            "name": self.name,
            "description": self.description,
            "mood": self.mood,
            "lighting": self.lighting,
            "visual_prompt_base": self.visual_prompt_base,
            "related_scene_ids": list(self.related_scene_ids),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Location":
        return cls(
            location_id=data["location_id"],
            name=data["name"],
            description=data.get("description", ""),
            mood=data.get("mood", ""),
            lighting=data.get("lighting", ""),
            visual_prompt_base=data.get("visual_prompt_base", ""),
            related_scene_ids=list(data.get("related_scene_ids", [])),
        )
