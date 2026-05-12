"""Service for manual AI Bible and Style analysis from source chapters."""

from __future__ import annotations

import json
from typing import Any

from app.domain.character import Character, CharacterOutfit, CharacterVariant
from app.domain.location import Location
from app.domain.project import Project
from app.domain.style_preset import StylePreset


class ManualAIBibleStyleService:
    def build_bible_style_analysis_prompt(
        self,
        project: Project,
        source_chapter_ids: list[str],
        style_hint: str | None = None
    ) -> str:
        chapters = []
        for cid in source_chapter_ids:
            for chapter in project.source_chapters:
                if chapter.chapter_id == cid:
                    chapters.append(chapter)
                    break

        if not chapters:
            return "No source chapters selected."

        source_text = "\n\n".join(
            [f"Chapter {chapter.chapter_number}: {chapter.title}\n{chapter.raw_text}" for chapter in chapters]
        )
        hint_text = f"\nStyle Hint: {style_hint}" if style_hint else ""

        prompt = f"""Task: Analyze the provided source story context and extract a comprehensive Bible and Style guide.
Return the result as a single JSON object.

Source Context:
{source_text}
{hint_text}

Required design:
Keep a base character identity, but create visual variants for different age-form stages and outfits.

A. Base characters
Use base Character only for identity/personality/role, not every visual state.
Fields: character_id, name, aliases, role, personality, relationship_notes.

B. Character age variants
Only create variants when the character has a major age/age-form difference (e.g., young form vs old form, child vs adult).
Do NOT create separate variants for temporary states, emotions, injuries, or poses (e.g., angry, injured, crying, battle pose, etc.).
Store temporary states as beat/storyboard fields later in Episode Planner. These belong in Beat fields, not as character variants.
Fields: variant_id, character_id, display_name, age_stage, age_description, gender, height, face_details, hair, eyes, body_type, skin_tone, visual_prompt_base, signature_features, continuity_must_keep, continuity_forbidden, negative_prompt_terms, default_outfit_id.

Allowed age_stage values:
- child
- teenager
- young_adult
- adult
- middle_aged
- old
- ancient
- reincarnated_child
- unknown

C. Outfit variants
Every distinct outfit should be a separate outfit object.
Fields: outfit_id, character_id, variant_id (optional), display_name, outfit_type, description, colors, materials, accessories, footwear, negative_prompt_terms.

D. Locations and Style Presets
Extract significant locations and suggest art style presets.

Rules for Bible / Style AI prompt:
- If a character has only one visual age-form, put the full visual profile directly on the character object.
- DO NOT create a default variant (e.g., char_001_default) for single-form characters.
- ONLY create character_variants entries if the character has multiple MAJOR age-form appearances (e.g. young vs old, child vs adult).
- DO NOT create variants for temporary emotional/physical/action states (angry, sad, injured, battle pose). These belong to beat fields.
- Outfit details should be stored directly on the character for single-form characters.
- Outfit details should be stored on the variant for multi-form characters.
- Every variant must have a clear visual_prompt_base.
- Every outfit must have a clear description.
- Variants and outfits must have stable IDs.
- Return JSON only. No markdown, no explanation.

Required JSON Schema:
{{
  "characters": [
    {{
      "character_id": "char_001",
      "name": "string",
      "aliases": ["string"],
      "role": "string",
      "gender": "string",
      "age_description": "string",
      "personality": "string",
      "relationship_notes": "string",

      "appearance": "string",
      "face_details": "string",
      "hair": "string",
      "eyes": "string",
      "body_type": "string",
      "skin_tone": "string",
      "height": "string",
      "visual_prompt_base": "string",
      "signature_features": ["string"],

      "default_outfit": "string",
      "outfit_details": "string",
      "outfit_colors": ["string"],
      "outfit_materials": ["string"],
      "accessories": ["string"],
      "footwear": "string",

      "continuity_must_keep": ["string"],
      "continuity_forbidden": ["string"],
      "negative_prompt_terms": ["string"],
      "reference_image_note": "string",

      "required_views": ["string"],
      "expression_set": ["string"],
      "micro_expression_set": ["string"],
      "head_angle_views": ["string"],
      "pose_set": ["string"],
      "hand_gesture_set": ["string"],
      "wardrobe_details": ["string"],
      "prop_details": ["string"],
      "color_palette": ["string"],
      "sheet_layout_style": "string",
      "reference_sheet_notes": "string"
    }}
  ],
  "character_variants": [
    {{
      "variant_id": "char_001_young",
      "character_id": "char_001",
      "display_name": "string",
      "age_stage": "child | teenager | young_adult | adult | middle_aged | old | ancient | reincarnated_child | unknown",
      "age_description": "string",
      "gender": "string",
      "height": "string",
      "face_details": "string",
      "hair": "string",
      "eyes": "string",
      "body_type": "string",
      "skin_tone": "string",
      "appearance": "string",
      "visual_prompt_base": "string",
      "signature_features": ["string"],
      "default_outfit": "string",
      "outfit_details": "string",
      "outfit_colors": ["string"],
      "outfit_materials": ["string"],
      "accessories": ["string"],
      "footwear": "string",
      "continuity_must_keep": ["string"],
      "continuity_forbidden": ["string"],
      "negative_prompt_terms": ["string"],
      "reference_image_note": "string",
      "required_views": "string",
      "expression_set": "string",
      "micro_expression_set": "string",
      "head_angle_views": "string",
      "pose_set": "string",
      "hand_gesture_set": "string",
      "wardrobe_details": "string",
      "prop_details": "string",
      "color_palette": "string",
      "sheet_layout_style": "string",
      "reference_sheet_notes": "string"
    }}
  ],
  "character_outfits": [
    {{
      "outfit_id": "outfit_char_001_formal",
      "character_id": "char_001",
      "variant_id": "char_001_young",
      "display_name": "string",
      "outfit_type": "formal | battle | travel | sleepwear | disguise",
      "description": "string",
      "colors": ["string"],
      "materials": ["string"],
      "accessories": ["string"],
      "footwear": "string",
      "negative_prompt_terms": ["string"]
    }}
  ],
  "locations": [
    {{
      "location_id": "loc_001",
      "name": "string",
      "aliases": ["string"],
      "location_type": "string",
      "description": "string",
      "mood": "string",
      "time_period": "string",
      "lighting": "string",
      "color_palette": "string",
      "architecture_style": "string",
      "recurring_props": ["string"],
      "visual_prompt_base": "string",
      "continuity_tags": ["string"],
      "negative_prompt_terms": ["string"]
    }}
  ],
  "style_presets": [
    {{
      "style_id": "string",
      "name": "string",
      "genre": "string",
      "positive_prompt": "string",
      "negative_prompt": "string",
      "line_style": "string",
      "color_palette": "string",
      "lighting_style": "string",
      "rendering_style": "string",
      "character_design_rules": "string",
      "background_detail_level": "string",
      "camera_style": "string",
      "mood_keywords": ["string"],
      "forbidden_terms": ["string"]
    }}
  ],
  "world_style_notes": {{
    "genre": "string",
    "era": "string",
    "tone": "string",
    "visual_world_rules": ["string"],
    "continuity_rules": ["string"]
  }}
}}
"""


        return prompt

    def apply_bible_style_analysis_result(
        self,
        project: Project,
        result_data: str | dict,
        overwrite: bool = False
    ) -> dict[str, int]:
        if isinstance(result_data, str):
            try:
                data = json.loads(result_data)
            except json.JSONDecodeError:
                # Handle potential markdown wrapping
                clean = result_data.strip()
                if clean.startswith("```json"):
                    clean = clean.split("```json")[1].split("```")[0].strip()
                elif clean.startswith("```"):
                    clean = clean.split("```")[1].split("```")[0].strip()
                data = json.loads(clean)
        else:
            data = result_data

        counts = {
            "characters": 0,
            "character_variants": 0,
            "character_outfits": 0,
            "locations": 0,
            "styles": 0,
        }

        # 1. Apply Characters
        for char_data in data.get("characters", []):
            if not isinstance(char_data, dict):
                continue
            cid = str(char_data.get("character_id", "")).strip()
            if not cid:
                continue

            existing = next((c for c in project.characters if c.character_id == cid), None)
            if not existing:
                new_char = Character.from_dict(char_data)
                if not new_char.character_id:
                    continue
                # Handle legacy nested reference_sheet_profile key
                if "reference_sheet_profile" in char_data:
                    from app.domain.character import _as_str_list as _asl
                    rsp = char_data["reference_sheet_profile"]
                    new_char.required_views = _asl(rsp.get("required_views", []))
                    new_char.expression_set = _asl(rsp.get("expression_set", []))
                    new_char.pose_set = _asl(rsp.get("pose_set", []))
                    new_char.color_palette = _asl(rsp.get("color_palette", []))
                    new_char.prop_details = _asl(rsp.get("prop_details", []))
                project.characters.append(new_char)
                counts["characters"] += 1
            else:
                self._merge_or_overwrite(existing, char_data, overwrite)
                # Handle legacy nested reference_sheet_profile key
                if "reference_sheet_profile" in char_data:
                    from app.domain.character import _as_str_list as _asl
                    rsp = char_data["reference_sheet_profile"]
                    self._set_val(existing, "required_views", _asl(rsp.get("required_views", [])), overwrite)
                    self._set_val(existing, "expression_set", _asl(rsp.get("expression_set", [])), overwrite)
                    self._set_val(existing, "pose_set", _asl(rsp.get("pose_set", [])), overwrite)
                    self._set_val(existing, "color_palette", _asl(rsp.get("color_palette", [])), overwrite)
                    self._set_val(existing, "prop_details", _asl(rsp.get("prop_details", [])), overwrite)
                counts["characters"] += 1

        # 2. Apply Character Variants
        for variant_data in data.get("character_variants", []):
            if not isinstance(variant_data, dict):
                continue
            variant_id = str(variant_data.get("variant_id", "")).strip()
            character_id = str(variant_data.get("character_id", "")).strip()
            if not variant_id or not character_id:
                continue

            character = self._get_or_create_character(project, character_id)
            existing_variant = next(
                (item for item in character.variants if item.variant_id == variant_id),
                None,
            )
            if existing_variant is None:
                variant = CharacterVariant.from_dict(variant_data)
                if not variant.display_name:
                    variant.display_name = variant.variant_id
                if not variant.character_id:
                    variant.character_id = character.character_id
                character.variants.append(variant)
            else:
                self._merge_or_overwrite(existing_variant, variant_data, overwrite)
            counts["character_variants"] += 1

        # Post-process migration: Merge back "default" variants if they are the only one
        for char in project.characters:
            if len(char.variants) == 1 and (char.variants[0].variant_id.endswith("_default") or char.variants[0].display_name.lower().endswith("mặc định")):
                v = char.variants[0]

                def _m_str(attr):
                    """Copy string attr from variant to base if base is empty."""
                    v_val = getattr(v, attr, "")
                    if not getattr(char, attr, ""):
                        setattr(char, attr, v_val)

                def _m_list(attr):
                    """Copy list attr from variant to base if base is empty."""
                    v_val = list(getattr(v, attr, []))
                    if not getattr(char, attr, []):
                        setattr(char, attr, v_val)

                _m_str("appearance")
                _m_str("face_details")
                _m_str("hair")
                _m_str("eyes")
                _m_str("body_type")
                _m_str("height")
                _m_str("skin_tone")
                _m_str("visual_prompt_base")
                _m_str("default_outfit")
                _m_str("outfit_details")
                _m_str("footwear")
                _m_str("reference_image_note")
                _m_str("sheet_layout_style")
                _m_str("reference_sheet_notes")

                _m_list("signature_features")
                _m_list("continuity_must_keep")
                _m_list("continuity_forbidden")
                _m_list("negative_prompt_terms")
                _m_list("outfit_colors")
                _m_list("outfit_materials")
                _m_list("accessories")
                _m_list("required_views")
                _m_list("expression_set")
                _m_list("micro_expression_set")
                _m_list("head_angle_views")
                _m_list("pose_set")
                _m_list("hand_gesture_set")
                _m_list("wardrobe_details")
                _m_list("prop_details")
                _m_list("color_palette")

                # Clear variants
                char.variants = []

        # 3. Apply Character Outfits
        for outfit_data in data.get("character_outfits", []):
            if not isinstance(outfit_data, dict):
                continue
            outfit_id = str(outfit_data.get("outfit_id", "")).strip()
            character_id = str(outfit_data.get("character_id", "")).strip()
            if not outfit_id or not character_id:
                continue

            character = self._get_or_create_character(project, character_id)
            existing_outfit = next(
                (item for item in character.outfits if item.outfit_id == outfit_id),
                None,
            )
            if existing_outfit is None:
                outfit = CharacterOutfit.from_dict(outfit_data)
                if not outfit.character_id:
                    outfit.character_id = character.character_id
                if not outfit.display_name:
                    outfit.display_name = outfit.outfit_id
                character.outfits.append(outfit)
            else:
                self._merge_or_overwrite(existing_outfit, outfit_data, overwrite)
            counts["character_outfits"] += 1

        # 4. Apply Locations
        for loc_data in data.get("locations", []):
            if not isinstance(loc_data, dict):
                continue
            lid = str(loc_data.get("location_id", "")).strip()
            if not lid:
                continue

            existing = next((l for l in project.locations if l.location_id == lid), None)
            if not existing:
                new_loc = Location.from_dict(loc_data)
                project.locations.append(new_loc)
                counts["locations"] += 1
            else:
                self._merge_or_overwrite(existing, loc_data, overwrite)
                counts["locations"] += 1

        # 5. Apply Style Presets
        for style_data in data.get("style_presets", []):
            if not isinstance(style_data, dict):
                continue
            sid = str(style_data.get("style_id", "")).strip()
            if not sid:
                continue

            existing = next((s for s in project.style_presets if s.style_id == sid), None)
            if not existing:
                new_style = StylePreset.from_dict(style_data)
                project.style_presets.append(new_style)
                counts["styles"] += 1
            else:
                self._merge_or_overwrite(existing, style_data, overwrite)
                counts["styles"] += 1

        # 6. World Style Notes
        if "world_style_notes" in data:
            if overwrite or not project.world_style_notes:
                project.world_style_notes = data["world_style_notes"]
            else:
                for k, v in data["world_style_notes"].items():
                    if k not in project.world_style_notes or not project.world_style_notes[k]:
                        project.world_style_notes[k] = v

        project.touch()
        return counts

    def _get_or_create_character(self, project: Project, character_id: str) -> Character:
        existing = next(
            (item for item in project.characters if item.character_id == character_id),
            None,
        )
        if existing:
            return existing

        placeholder = Character(
            character_id=character_id,
            name=character_id,
        )
        project.characters.append(placeholder)
        return placeholder

    def _merge_or_overwrite(self, obj: Any, data: dict, overwrite: bool) -> None:
        from app.domain.character import _as_str_list
        for key, value in data.items():
            if not hasattr(obj, key):
                continue
            if key in ("reference_sheet_profile", "character_id", "variant_id"):
                continue

            current = getattr(obj, key)
            # Normalise incoming value to match target type
            if isinstance(current, list):
                # Target expects list — ensure value is list[str]
                if not isinstance(value, list):
                    value = _as_str_list(value)
                else:
                    value = [str(x) for x in value if str(x).strip()]
            elif isinstance(current, str):
                # Target expects string — flatten list if needed
                if isinstance(value, list):
                    value = ", ".join(str(x) for x in value if str(x).strip())
                else:
                    value = str(value) if value is not None else ""

            self._set_val(obj, key, value, overwrite)

    def _set_val(self, obj: Any, key: str, value: Any, overwrite: bool) -> None:
        if not hasattr(obj, key):
            return

        current = getattr(obj, key)
        if overwrite:
            setattr(obj, key, value)
        else:
            if current is None or current == "" or current == []:
                setattr(obj, key, value)
