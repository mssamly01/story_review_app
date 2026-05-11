"""Deterministic image prompt builder.

This service updates Beat.image_prompt and Beat.negative_prompt only. It does
not call AI, create images, rewrite review text, or create beats.
"""

from __future__ import annotations

import re
from typing import Any

from app.domain.beat import Beat
from app.domain.character import Character
from app.domain.episode import ReviewEpisode
from app.domain.location import Location
from app.domain.project import Project
from app.domain.scene import Scene
from app.domain.style_preset import StylePreset
from app.infrastructure.ai_gateway import AIGateway


class PromptBuilderService:
    _safe_default_style = "cinematic webtoon style, high quality illustration"
    _base_negative_terms = [
        "low quality",
        "blurry",
        "distorted anatomy",
        "extra fingers",
        "inconsistent face",
        "wrong outfit",
        "text",
        "watermark",
        "logo",
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
        "text overlay",
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
                "episode": episode.to_dict(),
                "scene": scene.to_dict(),
                "beat": beat.to_dict(),
                "beat_id": beat.beat_id,
                "character_bible": [character.to_dict() for character in project.characters],
                "location_bible": [location.to_dict() for location in project.locations],
                "style_preset": style_preset.to_dict() if style_preset else {},
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
        components = [
            self._style_positive_prompt(style_preset),
            self._character_prompt(project, beat),
            self._location_prompt(project, beat, scene),
            f"visual focus: {beat.visual_description}" if beat.visual_description else "",
            f"action: {beat.action}" if beat.action else "",
            f"emotion: {beat.emotion}" if beat.emotion else "",
            f"camera: {beat.shot_type}" if beat.shot_type else "",
            f"mood: {scene.mood}" if scene.mood else "",
            "single clear visual moment",
            "coherent composition, masterpiece, high details",
        ]

        cleaned_components = [
            self._sanitize_positive_component(component)
            for component in components
            if component and component.strip()
        ]
        return ", ".join(cleaned_components)

    def _build_negative_prompt(
        self,
        project: Project,
        beat: Beat,
        scene: Scene,
        style_preset: StylePreset | None,
    ) -> str:
        terms = list(self._base_negative_terms)
        if style_preset and style_preset.negative_prompt:
            terms.extend(self._split_terms(style_preset.negative_prompt))
        if style_preset:
            terms.extend(style_preset.forbidden_terms)
        for character_id in beat.characters:
            character = self._find_character(project, character_id)
            if character:
                terms.extend(character.negative_prompt_terms)
        location = self._find_location(project, beat.location or scene.location)
        if location:
            terms.extend(location.negative_prompt_terms)
        return ", ".join(dict.fromkeys(terms))

    def _style_positive_prompt(self, style_preset: StylePreset | None) -> str:
        if not style_preset:
            return self._safe_default_style
        parts = [
            style_preset.positive_prompt or f"{style_preset.name}, high quality illustration",
            style_preset.line_style,
            style_preset.color_palette,
            style_preset.lighting_style,
            style_preset.rendering_style,
            style_preset.character_design_rules,
            style_preset.background_detail_level,
            style_preset.camera_style,
            ", ".join(style_preset.mood_keywords),
        ]
        return self._join_unique_parts(parts)

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
                name_part,
                f"wearing {character.default_outfit}" if character.default_outfit else "",
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
        parts = [
            location.visual_prompt_base,
            location.name,
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
        return self._join_unique_parts(parts)

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
        for blocked_term in self._positive_blocked_terms:
            cleaned = re.sub(
                rf"\b{re.escape(blocked_term)}\b",
                "",
                cleaned,
                flags=re.IGNORECASE,
            )
        return re.sub(r"\s+,", ",", re.sub(r"\s{2,}", " ", cleaned)).strip(" ,")

    def _split_terms(self, value: str) -> list[str]:
        return [term.strip() for term in value.split(",") if term.strip()]

    def _join_unique_parts(self, parts: list[str]) -> str:
        seen = set()
        cleaned_parts = []
        for part in parts:
            if not part:
                continue
            cleaned = re.sub(r"\s+", " ", part).strip(" ,")
            if cleaned and cleaned.lower() not in seen:
                cleaned_parts.append(cleaned)
                seen.add(cleaned.lower())
        return ", ".join(cleaned_parts)

    def _slug(self, value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
