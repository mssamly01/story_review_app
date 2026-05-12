"""Character bible entry domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(value)]


@dataclass(slots=True)
class CharacterVariant:
    variant_id: str
    character_id: str
    display_name: str = ""
    age_stage: str = "unknown"  # child, teenager, young_adult, adult, middle_aged, old, ancient, reincarnated_child, unknown
    state_type: str = ""  # legacy field
    age_description: str = ""
    gender: str = ""
    height: str = ""
    face_details: str = ""
    hair: str = ""
    eyes: str = ""
    body_type: str = ""
    skin_tone: str = ""
    appearance: str = ""
    voice_notes: str = ""
    relationship_notes: str = ""
    tags: list[str] = field(default_factory=list)
    visual_prompt_base: str = ""
    signature_features: list[str] = field(default_factory=list)

    # Outfit fields
    default_outfit: str = ""
    outfit_details: str = ""
    outfit_colors: list[str] = field(default_factory=list)
    outfit_materials: list[str] = field(default_factory=list)
    accessories: list[str] = field(default_factory=list)
    footwear: str = ""

    # Prompt/continuity
    continuity_must_keep: list[str] = field(default_factory=list)
    continuity_forbidden: list[str] = field(default_factory=list)
    negative_prompt_terms: list[str] = field(default_factory=list)
    reference_image_note: str = ""

    # Reference Sheet fields
    required_views: list[str] = field(default_factory=list)
    expression_set: list[str] = field(default_factory=list)
    micro_expression_set: list[str] = field(default_factory=list)
    head_angle_views: list[str] = field(default_factory=list)
    pose_set: list[str] = field(default_factory=list)
    hand_gesture_set: list[str] = field(default_factory=list)
    wardrobe_details: list[str] = field(default_factory=list)
    prop_details: list[str] = field(default_factory=list)
    color_palette: list[str] = field(default_factory=list)
    sheet_layout_style: str = ""
    reference_sheet_notes: str = ""

    default_outfit_id: str = ""  # legacy field

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "character_id": self.character_id,
            "display_name": self.display_name,
            "age_stage": self.age_stage,
            "state_type": self.state_type,
            "age_description": self.age_description,
            "gender": self.gender,
            "height": self.height,
            "face_details": self.face_details,
            "hair": self.hair,
            "eyes": self.eyes,
            "body_type": self.body_type,
            "skin_tone": self.skin_tone,
            "appearance": self.appearance,
            "voice_notes": self.voice_notes,
            "relationship_notes": self.relationship_notes,
            "tags": list(self.tags),
            "visual_prompt_base": self.visual_prompt_base,
            "signature_features": list(self.signature_features),
            "default_outfit": self.default_outfit,
            "outfit_details": self.outfit_details,
            "outfit_colors": list(self.outfit_colors),
            "outfit_materials": list(self.outfit_materials),
            "accessories": list(self.accessories),
            "footwear": self.footwear,
            "continuity_must_keep": list(self.continuity_must_keep),
            "continuity_forbidden": list(self.continuity_forbidden),
            "negative_prompt_terms": list(self.negative_prompt_terms),
            "reference_image_note": self.reference_image_note,
            "required_views": list(self.required_views),
            "expression_set": list(self.expression_set),
            "micro_expression_set": list(self.micro_expression_set),
            "head_angle_views": list(self.head_angle_views),
            "pose_set": list(self.pose_set),
            "hand_gesture_set": list(self.hand_gesture_set),
            "wardrobe_details": list(self.wardrobe_details),
            "prop_details": list(self.prop_details),
            "color_palette": list(self.color_palette),
            "sheet_layout_style": self.sheet_layout_style,
            "reference_sheet_notes": self.reference_sheet_notes,
            "default_outfit_id": self.default_outfit_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CharacterVariant":
        def _s(k, default=""):
            return str(data.get(k, default)).strip()

        return cls(
            variant_id=_s("variant_id"),
            character_id=_s("character_id"),
            display_name=_s("display_name"),
            age_stage=_s("age_stage", _s("state_type", "unknown")),
            state_type=_s("state_type"),
            age_description=_s("age_description"),
            gender=_s("gender"),
            height=_s("height"),
            face_details=_s("face_details"),
            hair=_s("hair"),
            eyes=_s("eyes"),
            body_type=_s("body_type"),
            skin_tone=_s("skin_tone"),
            appearance=_s("appearance"),
            voice_notes=_s("voice_notes"),
            relationship_notes=_s("relationship_notes"),
            tags=_as_str_list(data.get("tags", [])),
            visual_prompt_base=_s("visual_prompt_base"),
            signature_features=_as_str_list(data.get("signature_features", [])),
            default_outfit=_s("default_outfit"),
            outfit_details=_s("outfit_details"),
            outfit_colors=_as_str_list(data.get("outfit_colors", [])),
            outfit_materials=_as_str_list(data.get("outfit_materials", [])),
            accessories=_as_str_list(data.get("accessories", [])),
            footwear=_s("footwear"),
            continuity_must_keep=_as_str_list(data.get("continuity_must_keep", [])),
            continuity_forbidden=_as_str_list(data.get("continuity_forbidden", [])),
            negative_prompt_terms=_as_str_list(data.get("negative_prompt_terms", [])),
            reference_image_note=_s("reference_image_note"),
            required_views=_as_str_list(data.get("required_views", [])),
            expression_set=_as_str_list(data.get("expression_set", [])),
            micro_expression_set=_as_str_list(data.get("micro_expression_set", [])),
            head_angle_views=_as_str_list(data.get("head_angle_views", [])),
            pose_set=_as_str_list(data.get("pose_set", [])),
            hand_gesture_set=_as_str_list(data.get("hand_gesture_set", [])),
            wardrobe_details=_as_str_list(data.get("wardrobe_details", [])),
            prop_details=_as_str_list(data.get("prop_details", [])),
            color_palette=_as_str_list(data.get("color_palette", [])),
            sheet_layout_style=_s("sheet_layout_style"),
            reference_sheet_notes=_s("reference_sheet_notes"),
            default_outfit_id=_s("default_outfit_id"),
        )


@dataclass(slots=True)
class CharacterOutfit:
    outfit_id: str
    character_id: str
    variant_id: str = ""
    display_name: str = ""
    outfit_type: str = ""
    description: str = ""
    colors: list[str] = field(default_factory=list)
    materials: list[str] = field(default_factory=list)
    accessories: list[str] = field(default_factory=list)
    footwear: str = ""
    negative_prompt_terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outfit_id": self.outfit_id,
            "character_id": self.character_id,
            "variant_id": self.variant_id,
            "display_name": self.display_name,
            "outfit_type": self.outfit_type,
            "description": self.description,
            "colors": list(self.colors),
            "materials": list(self.materials),
            "accessories": list(self.accessories),
            "footwear": self.footwear,
            "negative_prompt_terms": list(self.negative_prompt_terms),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CharacterOutfit":
        def _s(k, default=""):
            return str(data.get(k, default)).strip()

        return cls(
            outfit_id=_s("outfit_id"),
            character_id=_s("character_id"),
            variant_id=_s("variant_id"),
            display_name=_s("display_name"),
            outfit_type=_s("outfit_type"),
            description=_s("description"),
            colors=_as_str_list(data.get("colors", [])),
            materials=_as_str_list(data.get("materials", [])),
            accessories=_as_str_list(data.get("accessories", [])),
            footwear=_s("footwear"),
            negative_prompt_terms=_as_str_list(data.get("negative_prompt_terms", [])),
        )


@dataclass(slots=True)
class Character:
    """
    Full character profile.

    Single-form characters (no variants) store all visual/outfit/continuity/reference
    fields directly on this object.

    Multi-form characters store shared identity here; each CharacterVariant holds the
    full visual profile for that age-form.
    """
    character_id: str
    name: str
    aliases: list[str] = field(default_factory=list)
    role: str = ""
    gender: str = ""
    age_description: str = ""
    personality: str = ""
    relationship_notes: str = ""
    continuity_tags: list[str] = field(default_factory=list)

    # Visual Profile (used directly for single-form characters)
    appearance: str = ""
    face_details: str = ""
    hair: str = ""
    eyes: str = ""
    body_type: str = ""
    height: str = ""
    skin_tone: str = ""
    visual_prompt_base: str = ""
    signature_features: list[str] = field(default_factory=list)

    # Outfit
    default_outfit: str = ""
    outfit_details: str = ""
    outfit_colors: list[str] = field(default_factory=list)
    outfit_materials: list[str] = field(default_factory=list)
    accessories: list[str] = field(default_factory=list)
    footwear: str = ""

    # Prompt / Continuity
    continuity_must_keep: list[str] = field(default_factory=list)
    continuity_forbidden: list[str] = field(default_factory=list)
    negative_prompt_terms: list[str] = field(default_factory=list)
    reference_image_note: str = ""

    # Reference Sheet
    required_views: list[str] = field(default_factory=list)
    expression_set: list[str] = field(default_factory=list)
    micro_expression_set: list[str] = field(default_factory=list)
    head_angle_views: list[str] = field(default_factory=list)
    pose_set: list[str] = field(default_factory=list)
    hand_gesture_set: list[str] = field(default_factory=list)
    wardrobe_details: list[str] = field(default_factory=list)
    prop_details: list[str] = field(default_factory=list)
    color_palette: list[str] = field(default_factory=list)
    sheet_layout_style: str = ""
    reference_sheet_notes: str = ""

    # Age-form variants (multi-form characters only)
    variants: list[CharacterVariant] = field(default_factory=list)
    outfits: list[CharacterOutfit] = field(default_factory=list)

    # Legacy / misc
    outfit_variants: list[str] = field(default_factory=list)
    voice_notes: str = ""
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
            "relationship_notes": self.relationship_notes,
            "continuity_tags": list(self.continuity_tags),
            "appearance": self.appearance,
            "face_details": self.face_details,
            "hair": self.hair,
            "eyes": self.eyes,
            "body_type": self.body_type,
            "height": self.height,
            "skin_tone": self.skin_tone,
            "visual_prompt_base": self.visual_prompt_base,
            "signature_features": list(self.signature_features),
            "default_outfit": self.default_outfit,
            "outfit_details": self.outfit_details,
            "outfit_colors": list(self.outfit_colors),
            "outfit_materials": list(self.outfit_materials),
            "accessories": list(self.accessories),
            "footwear": self.footwear,
            "continuity_must_keep": list(self.continuity_must_keep),
            "continuity_forbidden": list(self.continuity_forbidden),
            "negative_prompt_terms": list(self.negative_prompt_terms),
            "reference_image_note": self.reference_image_note,
            "required_views": list(self.required_views),
            "expression_set": list(self.expression_set),
            "micro_expression_set": list(self.micro_expression_set),
            "head_angle_views": list(self.head_angle_views),
            "pose_set": list(self.pose_set),
            "hand_gesture_set": list(self.hand_gesture_set),
            "wardrobe_details": list(self.wardrobe_details),
            "prop_details": list(self.prop_details),
            "color_palette": list(self.color_palette),
            "sheet_layout_style": self.sheet_layout_style,
            "reference_sheet_notes": self.reference_sheet_notes,
            "variants": [item.to_dict() for item in self.variants],
            "outfits": [item.to_dict() for item in self.outfits],
            "outfit_variants": list(self.outfit_variants),
            "voice_notes": self.voice_notes,
            "reference_image_paths": list(self.reference_image_paths),
            "sd_lora_name": self.sd_lora_name,
            "ip_adapter_image_path": self.ip_adapter_image_path,
            "character_embedding_hash": self.character_embedding_hash,
        }

    def find_variant(self, variant_id: str) -> CharacterVariant | None:
        for variant in self.variants:
            if variant.variant_id == variant_id:
                return variant
        return None

    def find_outfit(self, outfit_id: str) -> CharacterOutfit | None:
        for outfit in self.outfits:
            if outfit.outfit_id == outfit_id:
                return outfit
        return None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Character":
        def _s(k, default=""):
            return str(data.get(k, default)).strip()

        variants = [
            CharacterVariant.from_dict(item)
            for item in data.get("variants", [])
            if isinstance(item, dict)
        ]
        outfits = [
            CharacterOutfit.from_dict(item)
            for item in data.get("outfits", [])
            if isinstance(item, dict)
        ]

        # Backward compat: old projects stored some fields as comma-joined strings
        def _str_or_list(k) -> list[str]:
            v = data.get(k, [])
            if isinstance(v, list):
                return [str(x) for x in v if str(x).strip()]
            if isinstance(v, str) and v.strip():
                return [x.strip() for x in v.split(",") if x.strip()]
            return []

        return cls(
            character_id=_s("character_id"),
            name=_s("name"),
            aliases=_as_str_list(data.get("aliases", [])),
            role=_s("role"),
            gender=_s("gender"),
            age_description=_s("age_description"),
            personality=_s("personality"),
            relationship_notes=_s("relationship_notes"),
            continuity_tags=_as_str_list(data.get("continuity_tags", [])),
            appearance=_s("appearance"),
            face_details=_s("face_details"),
            hair=_s("hair"),
            eyes=_s("eyes"),
            body_type=_s("body_type"),
            height=_s("height"),
            skin_tone=_s("skin_tone"),
            visual_prompt_base=_s("visual_prompt_base"),
            signature_features=_str_or_list("signature_features"),
            default_outfit=_s("default_outfit"),
            outfit_details=_s("outfit_details"),
            outfit_colors=_as_str_list(data.get("outfit_colors", [])),
            outfit_materials=_as_str_list(data.get("outfit_materials", [])),
            accessories=_as_str_list(data.get("accessories", [])),
            footwear=_s("footwear"),
            continuity_must_keep=_str_or_list("continuity_must_keep"),
            continuity_forbidden=_str_or_list("continuity_forbidden"),
            negative_prompt_terms=_as_str_list(data.get("negative_prompt_terms", [])),
            reference_image_note=_s("reference_image_note"),
            required_views=_str_or_list("required_views"),
            expression_set=_str_or_list("expression_set"),
            micro_expression_set=_str_or_list("micro_expression_set"),
            head_angle_views=_str_or_list("head_angle_views"),
            pose_set=_str_or_list("pose_set"),
            hand_gesture_set=_str_or_list("hand_gesture_set"),
            wardrobe_details=_str_or_list("wardrobe_details"),
            prop_details=_str_or_list("prop_details"),
            color_palette=_str_or_list("color_palette"),
            sheet_layout_style=_s("sheet_layout_style"),
            reference_sheet_notes=_s("reference_sheet_notes"),
            variants=variants,
            outfits=outfits,
            outfit_variants=_as_str_list(data.get("outfit_variants", [])),
            voice_notes=_s("voice_notes"),
            reference_image_paths=_as_str_list(data.get("reference_image_paths", [])),
            sd_lora_name=_s("sd_lora_name"),
            ip_adapter_image_path=_s("ip_adapter_image_path"),
            character_embedding_hash=_s("character_embedding_hash"),
        )
