"""Service for building character reference sheet prompts."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.project import Project
    from app.domain.character import Character
    from app.domain.style_preset import StylePreset


class CharacterReferencePromptService:
    def build_reference_sheet_prompt(
        self,
        project: Project,
        character_id: str,
        style_preset_id: str | None = None,
        variant_id: str | None = None
    ) -> str:
        """Builds a comprehensive character reference sheet prompt."""
        character = self._find_character(project, character_id)
        style = self._find_style(project, style_preset_id)
        variant = character.find_variant(variant_id) if variant_id else None
        if not variant and len(character.variants) == 1:
            variant = character.variants[0]

        sections = []

        # 1. Header
        title = character.name
        if variant:
            title = f"{character.name} ({variant.display_name or variant.variant_id})"
        sections.append(f"CHARACTER REFERENCE SHEET: {title}")
        sections.append("Clean professional model sheet layout, white neutral background, clearly labeled panels.")

        # 2. Information & Identity
        gender = variant.gender if variant and variant.gender else character.gender
        age = variant.age_description if variant and variant.age_description else character.age_description
        role = character.role # Usually role is same across variants
        personality = character.personality # Usually personality is same
        
        info = [
            f"NAME: {character.name}",
            f"ROLE: {role}",
            f"GENDER: {gender}",
            f"AGE: {age}",
            f"PERSONALITY: {personality}"
        ]
        if character.aliases:
            info.insert(1, f"ALIASES: {', '.join(character.aliases)}")
        sections.append("## INFORMATION\n" + "\n".join(info))

        # 3. Visual Identity
        appearance = variant.appearance if variant and variant.appearance else character.appearance
        face = variant.face_details if variant and variant.face_details else character.face_details
        hair = variant.hair if variant and variant.hair else character.hair
        eyes = variant.eyes if variant and variant.eyes else character.eyes
        body = variant.body_type if variant and variant.body_type else character.body_type
        height = variant.height if variant and variant.height else character.height
        skin = variant.skin_tone if variant and variant.skin_tone else character.skin_tone
        sig_raw = variant.signature_features if variant else character.signature_features
        sig = ", ".join(sig_raw) if isinstance(sig_raw, list) else sig_raw
        prompt_base = variant.visual_prompt_base if variant and variant.visual_prompt_base else character.visual_prompt_base

        visual = [
            f"APPEARANCE: {appearance}",
            f"FACE: {face}",
            f"HAIR: {hair}",
            f"EYES: {eyes}",
            f"BODY: {body}",
        ]
        if height:
            visual.append(f"HEIGHT: {height}")
        if skin:
            visual.append(f"SKIN TONE: {skin}")
        visual.extend([
            f"SIGNATURE FEATURES: {sig}",
            f"PROMPT BASE: {prompt_base}"
        ])
        sections.append("## VISUAL IDENTITY\n" + "\n".join(visual))

        # 4. Outfits
        outfit_sec = []
        default_outfit = variant.default_outfit if variant and variant.default_outfit else character.default_outfit
        outfit_sec.append(f"DEFAULT OUTFIT: {default_outfit}")

        # Source outfit details from variant or base character
        src = variant if variant else character
        if src.outfit_details:
            outfit_sec.append(f"OUTFIT DETAILS: {src.outfit_details}")
        if src.outfit_colors:
            colors = src.outfit_colors if isinstance(src.outfit_colors, list) else [src.outfit_colors]
            outfit_sec.append(f"COLORS: {', '.join(colors)}")
        if src.outfit_materials:
            mats = src.outfit_materials if isinstance(src.outfit_materials, list) else [src.outfit_materials]
            outfit_sec.append(f"MATERIALS: {', '.join(mats)}")
        if src.accessories:
            acc = src.accessories if isinstance(src.accessories, list) else [src.accessories]
            outfit_sec.append(f"ACCESSORIES: {', '.join(acc)}")
        if src.footwear:
            outfit_sec.append(f"FOOTWEAR: {src.footwear}")

        wd_raw = getattr(src, "wardrobe_details", [])
        wd = ", ".join(wd_raw) if isinstance(wd_raw, list) else wd_raw
        if wd:
            outfit_sec.append(f"WARDROBE NOTES: {wd}")

        sections.append("## OUTFIT\n" + "\n".join(outfit_sec))

        # 5. Model Sheet Layout Details
        def _resolve(attr):
            """Get field from variant if set, else fall back to character."""
            v_val = getattr(variant, attr, None) if variant else None
            c_val = getattr(character, attr, None)
            val = v_val if v_val else c_val
            if isinstance(val, list):
                return ", ".join(val)
            return val or ""

        req_views = _resolve("required_views")
        expr_set = _resolve("expression_set")
        micro_expr = _resolve("micro_expression_set")
        angles = _resolve("head_angle_views")
        poses = _resolve("pose_set")
        hands = _resolve("hand_gesture_set")
        palette = _resolve("color_palette")
        layout_style = _resolve("sheet_layout_style")
        prop_det = _resolve("prop_details")

        layout = [
            f"FULL BODY TURNAROUND: {req_views or 'front view, 3/4 view, side view, back view'}",
            f"EXPRESSION SET: {expr_set or 'neutral, curious, worried, surprised, sad, determined, angry, relieved'}",
            f"MICRO EXPRESSIONS: {micro_expr or 'subtle eye twitches, lip pursing, eyebrow raises'}",
            f"HEAD ANGLES: {angles or 'front, 3/4 left, profile, 3/4 right, back, top view'}",
            f"POSES: {poses or 'relaxed stance, alert stance, confident stance, thoughtful pose'}",
            f"HAND GESTURES: {hands or 'relaxed hand, clenched fist, pointing, open hand, thinking pose'}",
            f"COLOR PALETTE: {palette or 'standard character palette'}"
        ]
        if prop_det:
            layout.append(f"PROPS: {prop_det}")
        if layout_style:
            layout.append(f"LAYOUT STYLE: {layout_style}")
        sections.append("## MODEL SHEET PANELS\n" + "\n".join(layout))

        # 6. Style Preset Integration
        if style:
            style_sec = [
                f"STYLE: {style.name}",
                f"POSITIVE PROMPT: {style.positive_prompt}",
                f"RENDERING: {style.rendering_style}",
                f"LIGHTING: {style.lighting_style}",
                f"DESIGN RULES: {style.character_design_rules}"
            ]
            sections.append("## ART STYLE & RENDERING\n" + "\n".join(style_sec))

        # 7. Continuity & Notes
        notes = []
        must_keep = variant.continuity_must_keep if variant else character.continuity_must_keep
        forbidden = variant.continuity_forbidden if variant else character.continuity_forbidden
        ref_notes = variant.reference_sheet_notes if variant and variant.reference_sheet_notes else character.reference_sheet_notes
        
        if must_keep:
            if isinstance(must_keep, list):
                notes.append(f"MUST KEEP: {', '.join(must_keep)}")
            else:
                notes.append(f"MUST KEEP: {must_keep}")
        if forbidden:
            if isinstance(forbidden, list):
                notes.append(f"FORBIDDEN: {', '.join(forbidden)}")
            else:
                notes.append(f"FORBIDDEN: {forbidden}")
        if ref_notes:
            notes.append(f"GENERAL NOTES: {ref_notes}")
        if notes:
            sections.append("## CONTINUITY & NOTES\n" + "\n".join(notes))

        # 8. Negative Prompt
        neg_terms = []
        if variant:
            neg_terms.extend(variant.negative_prompt_terms)
        else:
            neg_terms.extend(character.negative_prompt_terms)
            
        if style:
            neg_terms.extend(style.forbidden_terms)
        
        # Standard quality guards
        neg_terms.extend([
            "low quality", "blurry", "inconsistent face", "wrong outfit", 
            "different hairstyle", "distorted anatomy", "extra fingers", 
            "watermark", "logo", "messy unreadable text", "unrelated extra characters"
        ])
        
        sections.append("## NEGATIVE PROMPT (AVOID)\n" + ", ".join(set(neg_terms)))

        return "\n\n".join(sections)

    def _find_character(self, project: Project, character_id: str) -> Character:
        for char in project.characters:
            if char.character_id == character_id:
                return char
        raise LookupError(f"Character not found: {character_id}")

    def _find_style(self, project: Project, style_id: str | None) -> StylePreset | None:
        if not style_id:
            # Use default if available
            style_id = project.default_art_style
            
        if not style_id:
            return None
            
        for style in project.style_presets:
            if style.style_id == style_id:
                return style
        return None
