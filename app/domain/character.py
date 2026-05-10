"""Character bible entry domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Character:
    character_id: str
    name: str
    aliases: list[str] = field(default_factory=list)
    role: str = ""
    personality: str = ""
    appearance: str = ""
    default_outfit: str = ""
    voice_notes: str = ""
    visual_prompt_base: str = ""
    relationship_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "character_id": self.character_id,
            "name": self.name,
            "aliases": list(self.aliases),
            "role": self.role,
            "personality": self.personality,
            "appearance": self.appearance,
            "default_outfit": self.default_outfit,
            "voice_notes": self.voice_notes,
            "visual_prompt_base": self.visual_prompt_base,
            "relationship_notes": self.relationship_notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Character":
        return cls(
            character_id=data["character_id"],
            name=data["name"],
            aliases=list(data.get("aliases", [])),
            role=data.get("role", ""),
            personality=data.get("personality", ""),
            appearance=data.get("appearance", ""),
            default_outfit=data.get("default_outfit", ""),
            voice_notes=data.get("voice_notes", ""),
            visual_prompt_base=data.get("visual_prompt_base", ""),
            relationship_notes=data.get("relationship_notes", ""),
        )
