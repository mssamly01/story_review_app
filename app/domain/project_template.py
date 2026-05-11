"""Project onboarding template model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domain.style_preset import StylePreset


@dataclass(slots=True)
class ProjectTemplate:
    template_id: str
    name: str
    description: str = ""
    genre: str = ""
    default_language: str = "vi"
    default_narration_style: str = "mysterious"
    default_retelling_density: str = "full"
    default_art_style: str = ""
    recommended_chapters_per_episode: int = 1
    style_preset_ids: list[str] = field(default_factory=list)
    default_style_presets: list[StylePreset] = field(default_factory=list)
    prompt_guidelines: list[str] = field(default_factory=list)
    review_guidelines: list[str] = field(default_factory=list)
    character_bible_placeholders: list[dict[str, Any]] = field(default_factory=list)
    location_bible_placeholders: list[dict[str, Any]] = field(default_factory=list)
    export_defaults: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "genre": self.genre,
            "default_language": self.default_language,
            "default_narration_style": self.default_narration_style,
            "default_retelling_density": self.default_retelling_density,
            "default_art_style": self.default_art_style,
            "recommended_chapters_per_episode": self.recommended_chapters_per_episode,
            "style_preset_ids": list(self.style_preset_ids),
            "default_style_presets": [style.to_dict() for style in self.default_style_presets],
            "prompt_guidelines": list(self.prompt_guidelines),
            "review_guidelines": list(self.review_guidelines),
            "character_bible_placeholders": [
                dict(item) for item in self.character_bible_placeholders
            ],
            "location_bible_placeholders": [
                dict(item) for item in self.location_bible_placeholders
            ],
            "export_defaults": dict(self.export_defaults),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectTemplate":
        return cls(
            template_id=data["template_id"],
            name=data["name"],
            description=data.get("description", ""),
            genre=data.get("genre", ""),
            default_language=data.get("default_language", "vi"),
            default_narration_style=data.get(
                "default_narration_style",
                "mysterious",
            ),
            default_retelling_density=data.get("default_retelling_density", "full"),
            default_art_style=data.get("default_art_style", ""),
            recommended_chapters_per_episode=int(data.get("recommended_chapters_per_episode", 1)),
            style_preset_ids=list(data.get("style_preset_ids", [])),
            default_style_presets=[
                StylePreset.from_dict(style) for style in data.get("default_style_presets", [])
            ],
            prompt_guidelines=[str(value) for value in data.get("prompt_guidelines", [])],
            review_guidelines=[str(value) for value in data.get("review_guidelines", [])],
            character_bible_placeholders=[
                dict(value) for value in data.get("character_bible_placeholders", [])
            ],
            location_bible_placeholders=[
                dict(value) for value in data.get("location_bible_placeholders", [])
            ],
            export_defaults=dict(data.get("export_defaults", {})),
        )
