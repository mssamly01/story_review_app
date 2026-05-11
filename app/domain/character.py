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
    gender: str = ""
    age_description: str = ""
    personality: str = ""
    appearance: str = ""
    face_details: str = ""
    hair: str = ""
    eyes: str = ""
    body_type: str = ""
    default_outfit: str = ""
    outfit_variants: list[str] = field(default_factory=list)
    negative_prompt_terms: list[str] = field(default_factory=list)
    voice_notes: str = ""
    visual_prompt_base: str = ""
    relationship_notes: str = ""
    continuity_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "character_id": self.character_id,
            "name": self.name,
            "aliases": list(self.aliases),
            "role": self.role,
            "gender": self.gender,
            "age_description": self.age_description,
            "personality": self.personality,
            "appearance": self.appearance,
            "face_details": self.face_details,
            "hair": self.hair,
            "eyes": self.eyes,
            "body_type": self.body_type,
            "default_outfit": self.default_outfit,
            "outfit_variants": list(self.outfit_variants),
            "negative_prompt_terms": list(self.negative_prompt_terms),
            "voice_notes": self.voice_notes,
            "visual_prompt_base": self.visual_prompt_base,
            "relationship_notes": self.relationship_notes,
            "continuity_tags": list(self.continuity_tags),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Character":
        return cls(
            character_id=data["character_id"],
            name=data["name"],
            aliases=list(data.get("aliases", [])),
            role=data.get("role", ""),
            gender=data.get("gender", ""),
            age_description=data.get("age_description", ""),
            personality=data.get("personality", ""),
            appearance=data.get("appearance", ""),
            face_details=data.get("face_details", ""),
            hair=data.get("hair", ""),
            eyes=data.get("eyes", ""),
            body_type=data.get("body_type", ""),
            default_outfit=data.get("default_outfit", ""),
            outfit_variants=list(data.get("outfit_variants", [])),
            negative_prompt_terms=list(data.get("negative_prompt_terms", [])),
            voice_notes=data.get("voice_notes", ""),
            visual_prompt_base=data.get("visual_prompt_base", ""),
            relationship_notes=data.get("relationship_notes", ""),
            continuity_tags=list(data.get("continuity_tags", [])),
        )
