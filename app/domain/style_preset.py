"""Art style preset domain model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class StylePreset:
    style_id: str
    name: str
    description: str = ""
    positive_prompt: str = ""
    negative_prompt: str = ""
    lighting: str = ""
    character_design_rules: str = ""
    background_detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "style_id": self.style_id,
            "name": self.name,
            "description": self.description,
            "positive_prompt": self.positive_prompt,
            "negative_prompt": self.negative_prompt,
            "lighting": self.lighting,
            "character_design_rules": self.character_design_rules,
            "background_detail": self.background_detail,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StylePreset":
        return cls(
            style_id=data["style_id"],
            name=data["name"],
            description=data.get("description", ""),
            positive_prompt=data.get("positive_prompt", ""),
            negative_prompt=data.get("negative_prompt", ""),
            lighting=data.get("lighting", ""),
            character_design_rules=data.get("character_design_rules", ""),
            background_detail=data.get("background_detail", ""),
        )
