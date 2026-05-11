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
    
    # --- New Fields for Layer 1: Beat Prompt Character Data ---
    signature_features: str = ""
    continuity_must_keep: str = ""
    continuity_forbidden: str = ""
    reference_image_note: str = ""
    
    # --- New Fields for Layer 2: Character Reference Sheet Data ---
    required_views: str = ""
    expression_set: str = ""
    micro_expression_set: str = ""
    head_angle_views: str = ""
    pose_set: str = ""
    hand_gesture_set: str = ""
    wardrobe_details: str = ""
    prop_details: str = ""
    color_palette: str = ""
    sheet_layout_style: str = ""
    reference_sheet_notes: str = ""

    # Visual reference fields for image-model character consistency.
    reference_image_paths: list[str] = field(default_factory=list)
    sd_lora_name: str = ""
    ip_adapter_image_path: str = ""
    character_embedding_hash: str = ""

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
            "signature_features": self.signature_features,
            "continuity_must_keep": self.continuity_must_keep,
            "continuity_forbidden": self.continuity_forbidden,
            "reference_image_note": self.reference_image_note,
            "required_views": self.required_views,
            "expression_set": self.expression_set,
            "micro_expression_set": self.micro_expression_set,
            "head_angle_views": self.head_angle_views,
            "pose_set": self.pose_set,
            "hand_gesture_set": self.hand_gesture_set,
            "wardrobe_details": self.wardrobe_details,
            "prop_details": self.prop_details,
            "color_palette": self.color_palette,
            "sheet_layout_style": self.sheet_layout_style,
            "reference_sheet_notes": self.reference_sheet_notes,
            "reference_image_paths": list(self.reference_image_paths),
            "sd_lora_name": self.sd_lora_name,
            "ip_adapter_image_path": self.ip_adapter_image_path,
            "character_embedding_hash": self.character_embedding_hash,
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
            signature_features=data.get("signature_features", ""),
            continuity_must_keep=data.get("continuity_must_keep", ""),
            continuity_forbidden=data.get("continuity_forbidden", ""),
            reference_image_note=data.get("reference_image_note", ""),
            required_views=data.get("required_views", ""),
            expression_set=data.get("expression_set", ""),
            micro_expression_set=data.get("micro_expression_set", ""),
            head_angle_views=data.get("head_angle_views", ""),
            pose_set=data.get("pose_set", ""),
            hand_gesture_set=data.get("hand_gesture_set", ""),
            wardrobe_details=data.get("wardrobe_details", ""),
            prop_details=data.get("prop_details", ""),
            color_palette=data.get("color_palette", ""),
            sheet_layout_style=data.get("sheet_layout_style", ""),
            reference_sheet_notes=data.get("reference_sheet_notes", ""),
            reference_image_paths=list(data.get("reference_image_paths", [])),
            sd_lora_name=data.get("sd_lora_name", ""),
            ip_adapter_image_path=data.get("ip_adapter_image_path", ""),
            character_embedding_hash=data.get("character_embedding_hash", ""),
        )
