"""Deterministic image prompt builder.

This service updates Beat.image_prompt and Beat.negative_prompt only. It does
not call AI, create images, rewrite review text, or create beats.
"""

from __future__ import annotations

import re
from typing import Any

from app.domain.beat import Beat
from app.domain.character import Character, CharacterOutfit, CharacterVariant
from app.domain.episode import ReviewEpisode
from app.domain.location import Location
from app.domain.project import Project
from app.domain.scene import Scene
from app.domain.style_preset import StylePreset
from app.infrastructure.ai_gateway import AIGateway


class PromptBuilderService:
    _safe_default_style = (
        "high quality comic/webtoon illustration style, clean line art, "
        "detailed background"
    )
    _base_negative_terms = [
        "low quality",
        "blurry",
        "distorted anatomy",
        "bad hands",
        "extra fingers",
        "missing fingers",
        "inconsistent face",
        "wrong outfit",
        "different hairstyle",
        "wrong age",
        "wrong body proportions",
        "inconsistent location",
        "modern objects",
        "text",
        "subtitles",
        "captions",
        "speech bubble",
        "watermark",
        "logo",
        "signature",
        "duplicate character",
        "extra character",
        "multiple scenes in one image",
    ]
    _base_negative_aliases = [
        "caption",
        "subtitle",
        "speech bubble",
        "speech bubbles",
        "text overlay",
    ]
    _positive_blocked_terms = [
        "subtitles",
        "subtitle",
        "captions",
        "caption",
        "speech bubbles",
        "speech bubble",
        "watermark",
        "logo",
        "text",
        "text overlay",
        "visible text",
        "written words",
    ]

    def __init__(
        self,
        ai_gateway: AIGateway | None = None,
        use_ai: bool = False,
    ) -> None:
        self.ai_gateway = ai_gateway
        self.use_ai = use_ai

    def build_prompt_for_beat(
        self,
        project: Project,
        beat_id: str,
        style_preset_id: str | None = None,
    ) -> Beat:
        episode, scene, beat = self._find_beat_context(project, beat_id)
        style_preset = self._select_style_preset(project, style_preset_id)
        if self.use_ai:
            image_prompt, negative_prompt = self._build_prompt_with_ai(
                project=project,
                episode=episode,
                scene=scene,
                beat=beat,
                style_preset=style_preset,
            )
            beat.image_prompt = image_prompt
            beat.negative_prompt = negative_prompt
        else:
            beat.image_prompt = self._build_image_prompt(
                project=project,
                scene=scene,
                beat=beat,
                style_preset=style_preset,
            )
            beat.negative_prompt = self._build_negative_prompt(
                project,
                beat,
                scene,
                style_preset,
            )
        return beat

    def build_prompts_for_scene(
        self,
        project: Project,
        scene_id: str,
        style_preset_id: str | None = None,
    ) -> list[Beat]:
        episode, scene = self._find_scene_context(project, scene_id)
        style_preset = self._select_style_preset(project, style_preset_id)
        prompted_beats: list[Beat] = []
        for beat in scene.ordered_beats():
            if self.use_ai:
                image_prompt, negative_prompt = self._build_prompt_with_ai(
                    project=project,
                    episode=episode,
                    scene=scene,
                    beat=beat,
                    style_preset=style_preset,
                )
                beat.image_prompt = image_prompt
                beat.negative_prompt = negative_prompt
            else:
                beat.image_prompt = self._build_image_prompt(
                    project=project,
                    scene=scene,
                    beat=beat,
                    style_preset=style_preset,
                )
                beat.negative_prompt = self._build_negative_prompt(
                    project,
                    beat,
                    scene,
                    style_preset,
                )
            prompted_beats.append(beat)
        return prompted_beats

    def build_prompts_for_episode(
        self,
        project: Project,
        episode_id: str,
        style_preset_id: str | None = None,
    ) -> list[Beat]:
        episode = self._find_episode(project, episode_id)
        style_preset = self._select_style_preset(project, style_preset_id)
        prompted_beats: list[Beat] = []
        for scene in episode.scenes:
            for beat in scene.ordered_beats():
                if self.use_ai:
                    image_prompt, negative_prompt = self._build_prompt_with_ai(
                        project=project,
                        episode=episode,
                        scene=scene,
                        beat=beat,
                        style_preset=style_preset,
                    )
                    beat.image_prompt = image_prompt
                    beat.negative_prompt = negative_prompt
                else:
                    beat.image_prompt = self._build_image_prompt(
                        project=project,
                        scene=scene,
                        beat=beat,
                        style_preset=style_preset,
                    )
                    beat.negative_prompt = self._build_negative_prompt(
                        project,
                        beat,
                        scene,
                        style_preset,
                    )
                prompted_beats.append(beat)
        return prompted_beats

    def _build_prompt_with_ai(
        self,
        *,
        project: Project,
        episode: ReviewEpisode,
        scene: Scene,
        beat: Beat,
        style_preset: StylePreset | None,
    ) -> tuple[str, str]:
        gateway = self._require_ai_gateway()
        response = gateway.generate_json(
            "image_prompt_builder",
            {
                "episode": self._compact_episode(episode),
                "scene": self._compact_scene(scene),
                "beat": self._compact_beat(beat),
                "beat_id": beat.beat_id,
                "character_bible": [
                    self._compact_character(character)
                    for character in self._characters_for_beat(project, beat)
                ],
                "location_bible": [
                    self._compact_location(location)
                    for location in self._locations_for_beat(project, beat, scene)
                ],
                "style_preset": self._compact_style(style_preset),
            },
        )
        return self._prompts_from_ai_response(response, beat.beat_id)

    def _prompts_from_ai_response(self, response: dict[str, Any], beat_id: str) -> tuple[str, str]:
        if not isinstance(response, dict):
            raise ValueError("image_prompt_builder AI response must be a dict.")

        prompts = response.get("prompts", [])
        if not isinstance(prompts, list) or not prompts:
            raise ValueError(
                "image_prompt_builder AI response field 'prompts' must be a non-empty list."
            )

        selected_item = prompts[0]
        for item in prompts:
            if isinstance(item, dict) and item.get("beat_id") == beat_id:
                selected_item = item
                break

        if not isinstance(selected_item, dict):
            raise ValueError("image_prompt_builder AI prompt items must be dicts.")
        image_prompt = selected_item.get("image_prompt")
        negative_prompt = selected_item.get("negative_prompt")
        if not isinstance(image_prompt, str) or not image_prompt.strip():
            raise ValueError("image_prompt_builder AI image_prompt must be a non-empty string.")
        if not isinstance(negative_prompt, str) or not negative_prompt.strip():
            raise ValueError("image_prompt_builder AI negative_prompt must be a non-empty string.")
        return image_prompt, negative_prompt

    def _build_image_prompt(
        self,
        *,
        project: Project,
        scene: Scene,
        beat: Beat,
        style_preset: StylePreset | None,
    ) -> str:
        location = self._find_location(project, beat.location or scene.location)
        camera = self._camera_block(beat)
        time_of_day = self._time_of_day_block(beat, scene)
        location_block = self._location_block(location, beat, scene)
        lighting = self._lighting_block(beat, location, style_preset)
        character_block = self._characters_block(project, beat)
        action_block = self._action_block(beat)

        components = [
            self._style_positive_prompt(style_preset),
            camera,
            time_of_day,
            location_block,
            lighting,
            character_block,
            action_block,
            (
                "one clear visual moment, high quality illustration, "
                "consistent character design, consistent location design, no text"
            ),
        ]

        cleaned_components = [
            self._sanitize_positive_component(component)
            for component in components
            if component and component.strip()
        ]
        return ",\n".join(cleaned_components)

    def _build_negative_prompt(
        self,
        project: Project,
        beat: Beat,
        scene: Scene,
        style_preset: StylePreset | None,
    ) -> str:
        terms = list(self._base_negative_terms) + list(self._base_negative_aliases)
        if style_preset and style_preset.negative_prompt:
            terms.extend(self._split_terms(style_preset.negative_prompt))
        if style_preset:
            terms.extend(style_preset.forbidden_terms)
        for character_id in beat.characters:
            character = self._find_character(project, character_id)
            if character:
                terms.extend(character.negative_prompt_terms)
                variant = self._resolve_character_variant(character, beat, character_id)
                if variant:
                    terms.extend(variant.negative_prompt_terms)
                outfit = self._resolve_character_outfit(character, variant, beat, character_id)
                if outfit:
                    terms.extend(outfit.negative_prompt_terms)
        location = self._find_location(project, beat.location or scene.location)
        if location:
            terms.extend(location.negative_prompt_terms)
        return ", ".join(self._dedupe_terms(terms))

    def _style_positive_prompt(self, style_preset: StylePreset | None) -> str:
        if not style_preset:
            return self._safe_default_style
        parts = [
            style_preset.name,
            style_preset.positive_prompt,
            style_preset.line_style,
            style_preset.rendering_style,
            style_preset.color_palette,
            style_preset.character_design_rules,
            style_preset.camera_style,
            style_preset.lighting_style or style_preset.lighting,
            ", ".join(style_preset.mood_keywords),
        ]
        style = self._join_unique_parts(parts)
        return style or self._safe_default_style

    def _camera_block(self, beat: Beat) -> str:
        return beat.camera or beat.shot_type or "medium shot"

    def _time_of_day_block(self, beat: Beat, scene: Scene) -> str:
        value = beat.timeOfDay or getattr(beat, "time_of_day", "")
        value = value or getattr(scene, "timeOfDay", "") or getattr(scene, "time_of_day", "")
        if value:
            return str(value)

        lighting = " ".join([beat.lighting, beat.atmosphere]).lower()
        if any(term in lighting for term in ["moon", "night", "candle", "dark"]):
            return "Night"
        if "morning" in lighting or "sunrise" in lighting or "dawn" in lighting:
            return "Morning"
        if "dusk" in lighting or "sunset" in lighting or "twilight" in lighting:
            return "Dusk"
        return "daytime"

    def _location_block(
        self,
        location: Location | None,
        beat: Beat,
        scene: Scene,
    ) -> str:
        location_id = beat.location or scene.location
        cues = beat.location_cues or beat.visual_description or "no special location cues"
        asmr_visuals = beat.asmr_visuals or "subtle atmospheric details"

        if not location:
            location_name = location_id or "unknown location"
            return (
                f"Location: {location_name} (missing location profile), "
                f"location cues: {cues}, ASMR visuals: {asmr_visuals}"
            )

        profile = self._join_unique_parts(
            [
                location.visual_prompt_base,
                location.location_type,
                location.description,
                location.mood,
                location.time_period,
                location.lighting,
                location.color_palette,
                location.architecture_style,
                ", ".join(location.recurring_props),
                ", ".join(location.continuity_tags),
            ]
        )
        if not profile:
            profile = "missing location profile"
        return (
            f"Location: {location.name} ({profile}), "
            f"location cues: {cues}, ASMR visuals: {asmr_visuals}"
        )

    def _lighting_block(
        self,
        beat: Beat,
        location: Location | None,
        style_preset: StylePreset | None,
    ) -> str:
        parts = [
            beat.lighting,
            beat.atmosphere,
            location.lighting if location else "",
            style_preset.lighting_style if style_preset else "",
            style_preset.lighting if style_preset else "",
        ]
        return self._join_unique_parts(parts) or "cinematic lighting"

    def _characters_block(self, project: Project, beat: Beat) -> str:
        if not beat.characters:
            return "unknown character (missing character profile)"

        character_blocks: list[str] = []
        for character_id in beat.characters:
            character = self._find_character(project, character_id)
            if not character:
                character_blocks.append(f"{character_id} (missing character profile)")
                continue
            variant = self._resolve_character_variant(character, beat, character_id)
            outfit = self._resolve_character_outfit(character, variant, beat, character_id)
            character_blocks.append(
                self._character_full_description(
                    character,
                    beat,
                    character_id=character_id,
                    variant=variant,
                    outfit=outfit,
                )
            )
        return ", ".join(character_blocks)

    def _character_full_description(
        self,
        character: Character,
        beat: Beat,
        *,
        character_id: str,
        variant: CharacterVariant | None,
        outfit: CharacterOutfit | None,
    ) -> str:
        variant_display = variant.display_name if variant and variant.display_name else ""
        display_name = character.name
        if variant_display:
            if display_name.lower() not in variant_display.lower():
                display_name = f"{display_name} - {variant_display}"
            else:
                display_name = variant_display

        gender = variant.gender if variant and variant.gender else character.gender
        age = (
            variant.age_description
            if variant and variant.age_description
            else character.age_description
        )
        height = variant.height if variant and variant.height else getattr(character, "height", "")
        
        # Prioritize variant fields
        appearance = variant.appearance if variant and variant.appearance else character.appearance
        face = variant.face_details if variant and variant.face_details else character.face_details
        hair = variant.hair if variant and variant.hair else character.hair
        eyes = variant.eyes if variant and variant.eyes else character.eyes
        body = variant.body_type if variant and variant.body_type else character.body_type
        
        signature = self._join_unique_parts(
            [
                ", ".join(variant.signature_features) if variant else "",
                ", ".join(character.signature_features) if isinstance(character.signature_features, list) else character.signature_features if not variant else "",
            ]
        )
        visual_base = (
            variant.visual_prompt_base
            if variant and variant.visual_prompt_base
            else character.visual_prompt_base
        )
        
        # Per-character states from beat.character_states
        char_states = beat.character_states.get(character_id, {})
        posture = char_states.get("posture") or beat.posture
        expression = char_states.get("expression") or beat.expression
        body_language = char_states.get("body_language") or beat.body_language
        current_state = char_states.get("character_state") or beat.character_state
        wardrobe_notes = char_states.get("wardrobe_notes") or beat.wardrobe_notes
        # Outfit logic: build from variant > explicit outfit object > base character fields
        src_char_wardrobe = self._join_unique_parts([
            character.outfit_details or "",
            ", ".join(character.outfit_colors) if character.outfit_colors else "",
            ", ".join(character.outfit_materials) if character.outfit_materials else "",
            ", ".join(character.accessories) if character.accessories else "",
            character.footwear or "",
            ", ".join(character.wardrobe_details) if isinstance(character.wardrobe_details, list) else character.wardrobe_details or "",
        ])

        if variant and variant.default_outfit:
            outfit_description = self._join_unique_parts([
                variant.default_outfit,
                variant.outfit_details,
                ", ".join(variant.outfit_colors) if variant.outfit_colors else "",
                ", ".join(variant.outfit_materials) if variant.outfit_materials else "",
                ", ".join(variant.accessories) if variant.accessories else "",
                variant.footwear,
                wardrobe_notes
            ])
        else:
            outfit_description = self._join_unique_parts(
                [
                    self._outfit_description(outfit),
                    character.default_outfit if not outfit else "",
                    src_char_wardrobe if not outfit else "",
                    wardrobe_notes,
                ]
            )

        # Props and palette from character profile (character-level reference)
        char_props = ", ".join(character.prop_details) if isinstance(character.prop_details, list) else character.prop_details or ""
        char_palette = ", ".join(character.color_palette) if isinstance(character.color_palette, list) else character.color_palette or ""

        labelled_parts = [
            self._label("Gender", gender),
            self._label("Age", age),
            self._label("Height", height),
            self._label("Appearance", appearance),
            self._label("Face", face),
            self._label("Hair", hair),
            self._label("Eyes", eyes),
            self._label("Body", body),
            self._label("Visual base", visual_base),
            self._label("Signature features", signature),
            self._label("Posture", posture),
            self._label("Expression", expression),
            self._label("Body language", body_language),
            self._label("Current state", current_state),
            self._label("Outfit", outfit_description),
            self._label("Props", char_props),
            self._label("Color palette", char_palette),
        ]

        profile_content = ",\n".join([p for p in labelled_parts if p])
        if not profile_content:
            profile_content = "missing character profile"

        return f"{display_name} (\n{profile_content}\n)"


    def _action_block(self, beat: Beat) -> str:
        parts = [
            beat.action or "clear focused action",
            f"Visual description: {beat.visual_description}" if beat.visual_description else "",
            f"Emotion: {beat.emotion}" if beat.emotion else "",
            f"Composition: {beat.composition}" if beat.composition else "",
            f"Props: {', '.join(beat.props)}" if beat.props else "",
            f"Location state: {beat.location_state}" if beat.location_state else "",
            f"Transition note: {beat.transition_note}" if beat.transition_note else "",
        ]
        return self._join_unique_parts(parts)

    def _resolve_character_variant(
        self,
        character: Character,
        beat: Beat,
        character_id: str,
    ) -> CharacterVariant | None:
        variant_id = beat.character_variants.get(character_id)
        if not variant_id:
            variant_id = beat.character_variants.get(character.character_id, "")
        
        if variant_id:
            return character.find_variant(variant_id)
            
        # Fallback: if character has variants, use the first one as a safe default
        if len(character.variants) > 0:
            return character.variants[0]
            
        return None

    def _resolve_character_outfit(
        self,
        character: Character,
        variant: CharacterVariant | None,
        beat: Beat,
        character_id: str,
    ) -> CharacterOutfit | None:
        outfit_id = beat.character_outfits.get(character_id)
        if not outfit_id:
            outfit_id = beat.character_outfits.get(character.character_id, "")
        if not outfit_id and variant and variant.default_outfit_id:
            outfit_id = variant.default_outfit_id
        if not outfit_id:
            return None
        return character.find_outfit(outfit_id)

    def _outfit_description(self, outfit: CharacterOutfit | None) -> str:
        if not outfit:
            return ""
        parts = [
            outfit.description,
            ", ".join(outfit.colors),
            ", ".join(outfit.materials),
            ", ".join(outfit.accessories),
            outfit.footwear,
        ]
        return self._join_unique_parts(parts)

    def _label(self, label: str, value: str) -> str:
        value = str(value or "").strip()
        return f"{label}: {value}" if value else ""

    def _character_prompt(self, project: Project, beat: Beat) -> str:
        character_prompts: list[str] = []
        for character_id in beat.characters:
            character = self._find_character(project, character_id)
            if not character:
                character_prompts.append(character_id)
                continue

            # Smart concatenation to avoid repeating name if visual_prompt_base already has it
            name_part = character.name
            if (
                character.visual_prompt_base
                and character.name.lower() in character.visual_prompt_base.lower()
            ):
                name_part = ""

            parts = [
                character.visual_prompt_base,
                self._character_identity_block(character),
                name_part,
                f"wearing {character.default_outfit}" if character.default_outfit else "",
                self._character_outfit_variants(character),
                character.signature_features,
                f"keep consistent: {character.continuity_must_keep}" if character.continuity_must_keep else "",
            ]
            
            # If reference image or note exists, add consistency instruction
            if character.reference_image_paths or character.reference_image_note:
                parts.append("use the character reference sheet for visual consistency")
                if character.reference_image_note:
                    parts.append(f"({character.reference_image_note})")
            character_prompts.append(self._join_unique_parts(parts))
        return ", ".join(character_prompts)

    def _location_prompt(self, project: Project, beat: Beat, scene: Scene) -> str:
        location_id = beat.location or scene.location
        if not location_id:
            return ""
        location = self._find_location(project, location_id)
        if not location:
            return location_id
        profile = self._join_unique_parts(
            [
                location.visual_prompt_base,
                location.description,
                location.location_type,
                location.architecture_style,
                ", ".join(location.recurring_props),
                ", ".join(location.continuity_tags),
            ]
        )
        parts = [
            f"Location: {location.name} ({profile})" if profile else f"Location: {location.name}",
            location.mood,
            location.lighting,
            location.color_palette,
        ]
        return self._join_unique_parts(parts)

    def _character_identity_block(self, character: Character) -> str:
        parts = [
            character.gender,
            character.age_description,
            character.appearance,
            character.face_details,
            character.hair,
            character.eyes,
            character.body_type,
            character.wardrobe_details,
            character.prop_details,
            character.color_palette,
        ]
        block = self._join_unique_parts(parts)
        return f"{character.name} ({block})" if block else character.name

    def _character_outfit_variants(self, character: Character) -> str:
        if not character.outfit_variants:
            return ""
        return "outfit variants: " + "; ".join(character.outfit_variants)

    def _select_style_preset(
        self, project: Project, style_preset_id: str | None
    ) -> StylePreset | None:
        if style_preset_id:
            for style_preset in project.style_presets:
                if style_preset.style_id == style_preset_id:
                    return style_preset
            raise LookupError(f"StylePreset not found: {style_preset_id}")

        default_style_slug = self._slug(project.default_art_style)
        for style_preset in project.style_presets:
            if style_preset.style_id == project.default_art_style:
                return style_preset
            if self._slug(style_preset.style_id) == default_style_slug:
                return style_preset
            if self._slug(style_preset.name) == default_style_slug:
                return style_preset

        if project.style_presets:
            return project.style_presets[0]
        return None

    def _compact_episode(self, episode: ReviewEpisode) -> dict[str, Any]:
        return self._drop_empty(
            {
                "episode_id": episode.episode_id,
                "title": episode.title,
                "summary": episode.summary,
                "tone": episode.tone,
                "density": episode.density,
            }
        )

    def _compact_scene(self, scene: Scene) -> dict[str, Any]:
        return self._drop_empty(
            {
                "scene_id": scene.scene_id,
                "title": scene.title,
                "summary": scene.summary,
                "characters": list(scene.characters),
                "location": scene.location,
                "mood": scene.mood,
                "importance": scene.importance,
            }
        )

    def _compact_beat(self, beat: Beat) -> dict[str, Any]:
        return self._drop_empty(
            {
                "beat_id": beat.beat_id,
                "scene_id": beat.scene_id,
                "order_index": beat.order_index,
                "story_function": beat.story_function,
                "characters": list(beat.characters),
                "character_variants": dict(beat.character_variants),
                "character_outfits": dict(beat.character_outfits),
                "character_states": [
                    {
                        "character_id": character_id,
                        "variant_id": beat.character_variants.get(character_id, ""),
                        "outfit_id": beat.character_outfits.get(character_id, ""),
                        **beat.character_states.get(character_id, {})
                    }
                    for character_id in beat.characters
                ],
                "location": beat.location,
                "action": beat.action,
                "emotion": beat.emotion,
                "camera": beat.camera,
                "shot_type": beat.shot_type,
                "timeOfDay": beat.timeOfDay,
                "lighting": beat.lighting,
                "atmosphere": beat.atmosphere,
                "location_cues": beat.location_cues,
                "asmr_visuals": beat.asmr_visuals,
                "composition": beat.composition,
                "posture": beat.posture,
                "expression": beat.expression,
                "body_language": beat.body_language,
                "visual_description": beat.visual_description,
                "review_text_excerpt": self._shorten(beat.review_text, 260),
                "continuity_tags": list(beat.continuity_tags),
                "props": list(beat.props),
                "wardrobe_notes": beat.wardrobe_notes,
                "character_state": beat.character_state,
                "location_state": beat.location_state,
                "transition_note": beat.transition_note,
            }
        )

    def _compact_character(self, character: Character) -> dict[str, Any]:
        has_variants = len(character.variants) > 0
        return self._drop_empty(
            {
                "character_id": character.character_id,
                "name": character.name,
                "gender": character.gender,
                "age_description": character.age_description,
                "aliases": list(character.aliases),
                "visual_prompt_base": character.visual_prompt_base,
                "appearance": character.appearance,
                "face_details": character.face_details,
                "hair": character.hair,
                "eyes": character.eyes,
                "body_type": character.body_type,
                "height": character.height,
                "skin_tone": character.skin_tone,
                "signature_features": list(character.signature_features),
                "default_outfit": character.default_outfit,
                "outfit_details": character.outfit_details,
                "outfit_colors": list(character.outfit_colors),
                "outfit_materials": list(character.outfit_materials),
                "accessories": list(character.accessories),
                "footwear": character.footwear,
                "continuity_must_keep": list(character.continuity_must_keep),
                "continuity_forbidden": list(character.continuity_forbidden),
                "negative_prompt_terms": list(character.negative_prompt_terms),
                "variants": [
                    self._drop_empty(
                        {
                            "variant_id": item.variant_id,
                            "display_name": item.display_name or item.variant_id,
                            "age_stage": item.age_stage,
                            "age_description": item.age_description,
                            "gender": item.gender,
                            "visual_prompt_base": item.visual_prompt_base,
                            "appearance": item.appearance,
                            "face_details": item.face_details,
                            "hair": item.hair,
                            "eyes": item.eyes,
                            "body_type": item.body_type,
                            "height": item.height,
                            "skin_tone": item.skin_tone,
                            "default_outfit": item.default_outfit,
                            "outfit_details": item.outfit_details,
                            "outfit_colors": list(item.outfit_colors),
                            "outfit_materials": list(item.outfit_materials),
                            "accessories": list(item.accessories),
                            "footwear": item.footwear,
                            "signature_features": list(item.signature_features),
                            "continuity_must_keep": list(item.continuity_must_keep),
                            "continuity_forbidden": list(item.continuity_forbidden),
                            "negative_prompt_terms": list(item.negative_prompt_terms),
                        }
                    )
                    for item in character.variants
                ],
                "outfits": [
                    self._drop_empty(
                        {
                            "outfit_id": item.outfit_id,
                            "variant_id": item.variant_id,
                            "display_name": item.display_name or item.outfit_id,
                            "outfit_type": item.outfit_type,
                            "description": item.description,
                            "colors": list(item.colors),
                            "materials": list(item.materials),
                            "accessories": list(item.accessories),
                            "footwear": item.footwear,
                            "negative_prompt_terms": list(item.negative_prompt_terms),
                        }
                    )
                    for item in character.outfits
                ],
                # For single-form characters: combined appearance note for prompt
                "appearance_notes": self._join_unique_parts(
                    [
                        character.appearance,
                        character.face_details,
                        character.hair,
                        character.eyes,
                        character.body_type,
                        character.height,
                        character.skin_tone,
                        character.signature_features,
                        character.continuity_must_keep,
                    ]
                ) if not has_variants else "",
            }
        )

    def _compact_location(self, location: Location) -> dict[str, Any]:
        return self._drop_empty(
            {
                "location_id": location.location_id,
                "name": location.name,
                "aliases": list(location.aliases),
                "visual_prompt_base": location.visual_prompt_base,
                "mood": location.mood,
                "lighting": location.lighting,
                "setting_notes": self._join_unique_parts(
                    [
                        location.location_type,
                        location.description,
                        location.architecture_style,
                        ", ".join(location.recurring_props),
                        location.color_palette,
                    ]
                ),
                "negative_prompt_terms": list(location.negative_prompt_terms),
            }
        )

    def _compact_style(self, style_preset: StylePreset | None) -> dict[str, Any]:
        if not style_preset:
            return {}
        return self._drop_empty(
            {
                "style_id": style_preset.style_id,
                "name": style_preset.name,
                "positive_prompt": style_preset.positive_prompt,
                "negative_prompt": style_preset.negative_prompt,
                "forbidden_terms": list(style_preset.forbidden_terms),
                "lighting_style": style_preset.lighting_style,
                "color_palette": style_preset.color_palette,
                "character_design_rules": style_preset.character_design_rules,
            }
        )

    def _characters_for_beat(self, project: Project, beat: Beat) -> list[Character]:
        ids = set(beat.characters)
        return [
            character
            for character in project.characters
            if character.character_id in ids or character.name in ids
        ]

    def _locations_for_beat(
        self,
        project: Project,
        beat: Beat,
        scene: Scene,
    ) -> list[Location]:
        location_id = beat.location or scene.location
        if not location_id:
            return []
        location = self._find_location(project, location_id)
        return [location] if location else []

    def _drop_empty(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in data.items()
            if value not in (None, "", [], {})
        }

    def _shorten(self, value: str, limit: int) -> str:
        text = re.sub(r"\s+", " ", value).strip()
        if len(text) <= limit:
            return text
        return text[: limit - 1].rstrip() + "..."

    def _find_character(self, project: Project, character_id: str) -> Character | None:
        for character in project.characters:
            if character.character_id == character_id or character.name == character_id:
                return character
        return None

    def _find_location(self, project: Project, location_id: str) -> Location | None:
        for location in project.locations:
            if location.location_id == location_id or location.name == location_id:
                return location
        return None

    def _find_beat_context(
        self, project: Project, beat_id: str
    ) -> tuple[ReviewEpisode, Scene, Beat]:
        for episode in project.review_episodes:
            for scene in episode.scenes:
                for beat in scene.beats:
                    if beat.beat_id == beat_id:
                        return episode, scene, beat
        raise LookupError(f"Beat not found: {beat_id}")

    def _find_scene_context(self, project: Project, scene_id: str) -> tuple[ReviewEpisode, Scene]:
        for episode in project.review_episodes:
            for scene in episode.scenes:
                if scene.scene_id == scene_id:
                    return episode, scene
        raise LookupError(f"Scene not found: {scene_id}")

    def _find_episode(self, project: Project, episode_id: str) -> ReviewEpisode:
        for episode in project.review_episodes:
            if episode.episode_id == episode_id:
                return episode
        raise LookupError(f"ReviewEpisode not found: {episode_id}")

    def _require_ai_gateway(self) -> AIGateway:
        if self.ai_gateway is None:
            raise ValueError("use_ai=True requires an ai_gateway.")
        return self.ai_gateway

    def _sanitize_positive_component(self, component: str) -> str:
        cleaned = re.sub(r"\s+", " ", component).strip(" ,")
        no_text_marker = "__NO_TEXT_IN_IMAGE__"
        cleaned = re.sub(r"\bno text\b", no_text_marker, cleaned, flags=re.IGNORECASE)
        for blocked_term in self._positive_blocked_terms:
            cleaned = re.sub(
                rf"\b{re.escape(blocked_term)}\b",
                "",
                cleaned,
                flags=re.IGNORECASE,
            )
        cleaned = cleaned.replace(no_text_marker, "no text")
        return re.sub(r"\s+,", ",", re.sub(r"\s{2,}", " ", cleaned)).strip(" ,")

    def _split_terms(self, value: str) -> list[str]:
        return [term.strip() for term in value.split(",") if term.strip()]

    def _join_unique_parts(self, parts: list[Any]) -> str:
        seen = set()
        cleaned_parts = []
        for part in parts:
            if not part:
                continue
            
            # Robustness: ensure we are working with a string for regex operations
            if isinstance(part, list):
                part = ", ".join(str(i) for i in part)
            else:
                part = str(part)
                
            cleaned = re.sub(r"\s+", " ", part).strip(" ,")
            if cleaned and cleaned.lower() not in seen:
                cleaned_parts.append(cleaned)
                seen.add(cleaned.lower())
        return ", ".join(cleaned_parts)

    def _dedupe_terms(self, terms: list[str]) -> list[str]:
        seen = set()
        cleaned_terms: list[str] = []
        for term in terms:
            cleaned = re.sub(r"\s+", " ", str(term or "")).strip(" ,")
            if not cleaned:
                continue
            key = cleaned.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned_terms.append(cleaned)
        return cleaned_terms

    def _slug(self, value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
