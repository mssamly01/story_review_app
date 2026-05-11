"""Location bible entry domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Location:
    location_id: str
    name: str
    aliases: list[str] = field(default_factory=list)
    location_type: str = ""
    description: str = ""
    mood: str = ""
    time_period: str = ""
    lighting: str = ""
    color_palette: str = ""
    architecture_style: str = ""
    recurring_props: list[str] = field(default_factory=list)
    visual_prompt_base: str = ""
    negative_prompt_terms: list[str] = field(default_factory=list)
    continuity_tags: list[str] = field(default_factory=list)
    related_scene_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "location_id": self.location_id,
            "name": self.name,
            "aliases": list(self.aliases),
            "location_type": self.location_type,
            "description": self.description,
            "mood": self.mood,
            "time_period": self.time_period,
            "lighting": self.lighting,
            "color_palette": self.color_palette,
            "architecture_style": self.architecture_style,
            "recurring_props": list(self.recurring_props),
            "visual_prompt_base": self.visual_prompt_base,
            "negative_prompt_terms": list(self.negative_prompt_terms),
            "continuity_tags": list(self.continuity_tags),
            "related_scene_ids": list(self.related_scene_ids),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Location":
        return cls(
            location_id=data["location_id"],
            name=data["name"],
            aliases=list(data.get("aliases", [])),
            location_type=data.get("location_type", ""),
            description=data.get("description", ""),
            mood=data.get("mood", ""),
            time_period=data.get("time_period", ""),
            lighting=data.get("lighting", ""),
            color_palette=data.get("color_palette", ""),
            architecture_style=data.get("architecture_style", ""),
            recurring_props=list(data.get("recurring_props", [])),
            visual_prompt_base=data.get("visual_prompt_base", ""),
            negative_prompt_terms=list(data.get("negative_prompt_terms", [])),
            continuity_tags=list(data.get("continuity_tags", [])),
            related_scene_ids=list(data.get("related_scene_ids", [])),
        )
