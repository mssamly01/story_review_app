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
        style_preset_id: str | None = None
    ) -> str:
        """Builds a comprehensive character reference sheet prompt."""
        character = self._find_character(project, character_id)
        style = self._find_style(project, style_preset_id)

        sections = []

        # 1. Header
        sections.append(f"CHARACTER REFERENCE SHEET: {character.name}")
        sections.append("Clean professional model sheet layout, white neutral background, clearly labeled panels.")

        # 2. Information & Identity
        info = [
            f"NAME: {character.name}",
            f"ROLE: {character.role}",
            f"GENDER: {character.gender}",
            f"AGE: {character.age_description}",
            f"PERSONALITY: {character.personality}"
        ]
        if character.aliases:
            info.insert(1, f"ALIASES: {', '.join(character.aliases)}")
        sections.append("## INFORMATION\n" + "\n".join(info))

        # 3. Visual Identity
        visual = [
            f"APPEARANCE: {character.appearance}",
            f"FACE: {character.face_details}",
            f"HAIR: {character.hair}",
            f"EYES: {character.eyes}",
            f"BODY: {character.body_type}",
            f"SIGNATURE FEATURES: {character.signature_features}",
            f"PROMPT BASE: {character.visual_prompt_base}"
        ]
        sections.append("## VISUAL IDENTITY\n" + "\n".join(visual))

        # 4. Outfits
        outfit_sec = [f"DEFAULT OUTFIT: {character.default_outfit}"]
        if character.outfit_variants:
            outfit_sec.append(f"VARIANTS: {', '.join(character.outfit_variants)}")
        if character.wardrobe_details:
            outfit_sec.append(f"WARDROBE DETAILS: {character.wardrobe_details}")
        sections.append("## OUTFIT & WARDROBE\n" + "\n".join(outfit_sec))

        # 5. Model Sheet Layout Details
        layout = [
            f"FULL BODY TURNAROUND: {character.required_views or 'front view, 3/4 view, side view, back view'}",
            f"EXPRESSION SET: {character.expression_set or 'neutral, curious, worried, surprised, sad, determined, angry, relieved'}",
            f"MICRO EXPRESSIONS: {character.micro_expression_set or 'subtle eye twitches, lip pursing, eyebrow raises'}",
            f"HEAD ANGLES: {character.head_angle_views or 'front, 3/4 left, profile, 3/4 right, back, top view'}",
            f"POSES: {character.pose_set or 'relaxed stance, alert stance, confident stance, thoughtful pose'}",
            f"HAND GESTURES: {character.hand_gesture_set or 'relaxed hand, clenched fist, pointing, open hand, thinking pose'}",
            f"COLOR PALETTE: {character.color_palette or 'standard character palette'}"
        ]
        if character.prop_details:
            layout.append(f"PROPS: {character.prop_details}")
        if character.sheet_layout_style:
            layout.append(f"LAYOUT STYLE: {character.sheet_layout_style}")
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
        if character.continuity_must_keep:
            notes.append(f"MUST KEEP: {character.continuity_must_keep}")
        if character.continuity_forbidden:
            notes.append(f"FORBIDDEN: {character.continuity_forbidden}")
        if character.reference_sheet_notes:
            notes.append(f"GENERAL NOTES: {character.reference_sheet_notes}")
        if notes:
            sections.append("## CONTINUITY & NOTES\n" + "\n".join(notes))

        # 8. Negative Prompt
        neg_terms = list(character.negative_prompt_terms)
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
