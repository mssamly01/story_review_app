"""Service for building character reference sheet prompts."""

from __future__ import annotations

from app.domain.project import Project


class CharacterReferencePromptService:
    def build_reference_sheet_prompt(
        self,
        project: Project,
        character_id: str,
        style_preset_id: str | None = None
    ) -> str:
        character = None
        for char in project.characters:
            if char.character_id == character_id or char.name == character_id:
                character = char
                break
        
        if not character:
            raise LookupError(f"Character not found: {character_id}")

        style_preset = None
        target_style_id = style_preset_id or project.default_art_style
        for preset in project.style_presets:
            if preset.style_id == target_style_id or preset.name == target_style_id:
                style_preset = preset
                break

        components = []
        
        # Style part
        if style_preset:
            components.append(f"Style: {style_preset.positive_prompt}")
        
        # Core Identity
        components.append(f"Character: {character.name}")
        if character.visual_prompt_base:
            components.append(character.visual_prompt_base)
        
        # Reference Sheet Data
        sheet_data = []
        if character.required_views:
            sheet_data.append(f"Required views: {character.required_views}")
        if character.expression_set:
            sheet_data.append(f"Expression set: {character.expression_set}")
        if character.micro_expression_set:
            sheet_data.append(f"Micro-expressions: {character.micro_expression_set}")
        if character.head_angle_views:
            sheet_data.append(f"Head angles: {character.head_angle_views}")
        if character.pose_set:
            sheet_data.append(f"Pose set: {character.pose_set}")
        if character.hand_gesture_set:
            sheet_data.append(f"Hand gestures: {character.hand_gesture_set}")
        if character.wardrobe_details:
            sheet_data.append(f"Wardrobe: {character.wardrobe_details}")
        if character.prop_details:
            sheet_data.append(f"Props: {character.prop_details}")
        if character.color_palette:
            sheet_data.append(f"Color palette: {character.color_palette}")
        if character.sheet_layout_style:
            sheet_data.append(f"Layout style: {character.sheet_layout_style}")
        if character.reference_sheet_notes:
            sheet_data.append(f"Notes: {character.reference_sheet_notes}")
            
        if sheet_data:
            components.append("--- Character Reference Sheet Specification ---")
            components.extend(sheet_data)
            
        return "\n".join(components)
