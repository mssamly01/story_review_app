"""Art style preset domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class StylePreset:
    style_id: str
    name: str
    description: str = ""
    positive_prompt: str = ""
    negative_prompt: str = ""
    genre: str = ""
    line_style: str = ""
    color_palette: str = ""
    lighting: str = ""
    lighting_style: str = ""
    rendering_style: str = ""
    character_design_rules: str = ""
    background_detail: str = ""
    background_detail_level: str = ""
    camera_style: str = ""
    mood_keywords: list[str] = field(default_factory=list)
    forbidden_terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "style_id": self.style_id,
            "name": self.name,
            "description": self.description,
            "positive_prompt": self.positive_prompt,
            "negative_prompt": self.negative_prompt,
            "genre": self.genre,
            "line_style": self.line_style,
            "color_palette": self.color_palette,
            "lighting": self.lighting,
            "lighting_style": self.lighting_style,
            "rendering_style": self.rendering_style,
            "character_design_rules": self.character_design_rules,
            "background_detail": self.background_detail,
            "background_detail_level": self.background_detail_level,
            "camera_style": self.camera_style,
            "mood_keywords": list(self.mood_keywords),
            "forbidden_terms": list(self.forbidden_terms),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StylePreset":
        background_detail = data.get("background_detail", "")
        background_detail_level = data.get(
            "background_detail_level",
            background_detail,
        )
        return cls(
            style_id=data["style_id"],
            name=data["name"],
            description=data.get("description", ""),
            positive_prompt=data.get("positive_prompt", ""),
            negative_prompt=data.get("negative_prompt", ""),
            genre=data.get("genre", ""),
            line_style=data.get("line_style", ""),
            color_palette=data.get("color_palette", ""),
            lighting=data.get("lighting", ""),
            lighting_style=data.get("lighting_style", ""),
            rendering_style=data.get("rendering_style", ""),
            character_design_rules=data.get("character_design_rules", ""),
            background_detail=background_detail,
            background_detail_level=background_detail_level,
            camera_style=data.get("camera_style", ""),
            mood_keywords=list(data.get("mood_keywords", [])),
            forbidden_terms=list(data.get("forbidden_terms", [])),
        )
