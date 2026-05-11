"""Service for manual AI Bible and Style analysis from source chapters."""

from __future__ import annotations

import json
from typing import Any

from app.domain.character import Character
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
            for ch in project.source_chapters:
                if ch.chapter_id == cid:
                    chapters.append(ch)
                    break
        
        if not chapters:
            return "No source chapters selected."

        source_text = "\n\n".join([f"Chapter {ch.chapter_number}: {ch.title}\n{ch.raw_text}" for ch in chapters])
        
        hint_text = f"\nStyle Hint: {style_hint}" if style_hint else ""

        prompt = f"""Task: Analyze the provided source story context and extract a comprehensive Bible and Style guide.
Return the result as a single JSON object.

Source Context:
{source_text}
{hint_text}

Instructions:
1. Extract all significant characters.
2. Extract all significant locations.
3. Suggest at least one art style preset suitable for a webtoon/manhwa adaptation of this story.
4. Extract world style notes (genre, era, tone, visual rules).

Rules:
- Analyze ONLY from the provided source context.
- If a detail is missing, infer cautiously or leave generic. Do not invent major facts.
- Return JSON ONLY. No markdown, no explanation, no preamble.

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
      "appearance": "string",
      "face_details": "string",
      "hair": "string",
      "eyes": "string",
      "body_type": "string",
      "default_outfit": "string",
      "signature_features": ["string"],
      "visual_prompt_base": "string",
      "continuity_must_keep": ["string"],
      "continuity_forbidden": ["string"],
      "negative_prompt_terms": ["string"],
      "reference_sheet_profile": {{
        "required_views": ["front", "3/4 view", "side", "back"],
        "expression_set": ["neutral", "shocked", "determined"],
        "pose_set": ["relaxed stance", "alert stance"],
        "color_palette": ["string"],
        "prop_details": ["string"]
      }}
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

        counts = {"characters": 0, "locations": 0, "styles": 0}

        # 1. Apply Characters
        for char_data in data.get("characters", []):
            cid = char_data.get("character_id")
            if not cid: continue
            
            existing = next((c for c in project.characters if c.character_id == cid), None)
            if not existing:
                # Create new
                new_char = Character.from_dict(char_data)
                # Map reference_sheet_profile if present
                if "reference_sheet_profile" in char_data:
                    rsp = char_data["reference_sheet_profile"]
                    new_char.required_views = ", ".join(rsp.get("required_views", []))
                    new_char.expression_set = ", ".join(rsp.get("expression_set", []))
                    new_char.pose_set = ", ".join(rsp.get("pose_set", []))
                    new_char.color_palette = ", ".join(rsp.get("color_palette", []))
                    new_char.prop_details = ", ".join(rsp.get("prop_details", []))
                
                # Special mapping for list fields
                if isinstance(char_data.get("signature_features"), list):
                    new_char.signature_features = ", ".join(char_data["signature_features"])
                if isinstance(char_data.get("continuity_must_keep"), list):
                    new_char.continuity_must_keep = ", ".join(char_data["continuity_must_keep"])
                if isinstance(char_data.get("continuity_forbidden"), list):
                    new_char.continuity_forbidden = ", ".join(char_data["continuity_forbidden"])
                
                project.characters.append(new_char)
                counts["characters"] += 1
            else:
                # Update existing
                self._merge_or_overwrite(existing, char_data, overwrite)
                # Handle complex nested mapping for existing
                if "reference_sheet_profile" in char_data:
                    rsp = char_data["reference_sheet_profile"]
                    self._set_val(existing, "required_views", ", ".join(rsp.get("required_views", [])), overwrite)
                    self._set_val(existing, "expression_set", ", ".join(rsp.get("expression_set", [])), overwrite)
                    self._set_val(existing, "pose_set", ", ".join(rsp.get("pose_set", [])), overwrite)
                    self._set_val(existing, "color_palette", ", ".join(rsp.get("color_palette", [])), overwrite)
                    self._set_val(existing, "prop_details", ", ".join(rsp.get("prop_details", [])), overwrite)
                
                if isinstance(char_data.get("signature_features"), list):
                    self._set_val(existing, "signature_features", ", ".join(char_data["signature_features"]), overwrite)
                if isinstance(char_data.get("continuity_must_keep"), list):
                    self._set_val(existing, "continuity_must_keep", ", ".join(char_data["continuity_must_keep"]), overwrite)
                if isinstance(char_data.get("continuity_forbidden"), list):
                    self._set_val(existing, "continuity_forbidden", ", ".join(char_data["continuity_forbidden"]), overwrite)
                
                counts["characters"] += 1

        # 2. Apply Locations
        for loc_data in data.get("locations", []):
            lid = loc_data.get("location_id")
            if not lid: continue
            
            existing = next((l for l in project.locations if l.location_id == lid), None)
            if not existing:
                new_loc = Location.from_dict(loc_data)
                project.locations.append(new_loc)
                counts["locations"] += 1
            else:
                self._merge_or_overwrite(existing, loc_data, overwrite)
                counts["locations"] += 1

        # 3. Apply Style Presets
        for style_data in data.get("style_presets", []):
            sid = style_data.get("style_id")
            if not sid: continue
            
            existing = next((s for s in project.style_presets if s.style_id == sid), None)
            if not existing:
                new_style = StylePreset.from_dict(style_data)
                project.style_presets.append(new_style)
                counts["styles"] += 1
            else:
                self._merge_or_overwrite(existing, style_data, overwrite)
                counts["styles"] += 1

        # 4. World Style Notes
        if "world_style_notes" in data:
            if overwrite or not project.world_style_notes:
                project.world_style_notes = data["world_style_notes"]
            else:
                # Merge keys
                for k, v in data["world_style_notes"].items():
                    if k not in project.world_style_notes or not project.world_style_notes[k]:
                        project.world_style_notes[k] = v

        project.touch()
        return counts

    def _merge_or_overwrite(self, obj: Any, data: dict, overwrite: bool) -> None:
        for key, value in data.items():
            if not hasattr(obj, key): continue
            
            # Skip non-serializable complex fields not in to_dict
            if key == "reference_sheet_profile": continue
            
            # Normalize lists to strings if needed for the domain model
            if isinstance(value, list) and isinstance(getattr(obj, key), str):
                value = ", ".join(value)
            
            self._set_val(obj, key, value, overwrite)

    def _set_val(self, obj: Any, key: str, value: Any, overwrite: bool) -> None:
        if not hasattr(obj, key): return
        
        current = getattr(obj, key)
        if overwrite:
            setattr(obj, key, value)
        else:
            # Merge: only if current is empty
            if current is None or current == "" or current == []:
                setattr(obj, key, value)
