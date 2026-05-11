"""Deterministic continuity checks for episodes, scenes, and beats."""

from __future__ import annotations

import re
from typing import Any

from app.domain.project import Project
from app.domain.validation import ValidationIssue
from app.services.project_service import ProjectService


class ContinuityCheckerService:
    BLOCKED_PROMPT_TERMS = [
        "caption",
        "captions",
        "logo",
        "speech bubble",
        "speech bubbles",
        "subtitle",
        "subtitles",
        "text",
        "watermark",
    ]

    TERM_STOPWORDS = {
        "and",
        "are",
        "cinematic",
        "detailed",
        "high",
        "illustration",
        "quality",
        "style",
        "the",
        "with",
    }

    TRANSITION_FUNCTIONS = {"reaction", "transition", "reveal", "cliffhanger"}

    def __init__(self, project_service: ProjectService | None = None) -> None:
        self.project_service = project_service or ProjectService()

    def check_episode(self, project: Project, episode_id: str) -> list[ValidationIssue]:
        episode = self.project_service.find_episode(project, episode_id)
        issues: list[ValidationIssue] = []
        for scene in episode.scenes:
            self._check_scene_object(project, episode_id, scene, issues)
        return issues

    def check_scene(self, project: Project, scene_id: str) -> list[ValidationIssue]:
        episode, scene = self._find_scene(project, scene_id)
        issues: list[ValidationIssue] = []
        self._check_scene_object(project, episode.episode_id, scene, issues)
        return issues

    def check_beat(self, project: Project, beat_id: str) -> list[ValidationIssue]:
        episode, scene, beat = self._find_beat(project, beat_id)
        issues: list[ValidationIssue] = []
        self._check_beat_object(
            project,
            episode.episode_id,
            scene.scene_id,
            beat,
            issues,
        )
        return issues

    def _check_scene_object(
        self,
        project: Project,
        episode_id: str,
        scene: Any,
        issues: list[ValidationIssue],
    ) -> None:
        previous_emotion = ""
        for beat in scene.ordered_beats():
            self._check_beat_object(
                project,
                episode_id,
                scene.scene_id,
                beat,
                issues,
            )
            current_emotion = str(getattr(beat, "emotion", "")).strip()
            if (
                previous_emotion
                and current_emotion
                and previous_emotion != current_emotion
                and getattr(beat, "story_function", "") not in self.TRANSITION_FUNCTIONS
            ):
                self._add_issue(
                    issues,
                    severity="info",
                    category="emotion_continuity",
                    message=(
                        f"Emotion changes from {previous_emotion} to "
                        f"{current_emotion} before beat {beat.beat_id}."
                    ),
                    suggestion="Check whether the emotional shift has enough setup.",
                    entity_type="Beat",
                    entity_id=beat.beat_id,
                    episode_id=episode_id,
                    scene_id=scene.scene_id,
                    beat_id=beat.beat_id,
                )
            previous_emotion = current_emotion or previous_emotion

    def _check_beat_object(
        self,
        project: Project,
        episode_id: str,
        scene_id: str,
        beat: Any,
        issues: list[ValidationIssue],
    ) -> None:
        beat_id = getattr(beat, "beat_id", "")
        characters_by_id = {character.character_id: character for character in project.characters}
        locations_by_id = {location.location_id: location for location in project.locations}
        image_prompt = str(getattr(beat, "image_prompt", "") or "")
        negative_prompt = str(getattr(beat, "negative_prompt", "") or "")
        review_text = str(getattr(beat, "review_text", "") or "")

        for character_id in list(getattr(beat, "characters", []) or []):
            character = characters_by_id.get(character_id)
            if character is None:
                self._add_issue(
                    issues,
                    severity="error",
                    category="broken_reference",
                    message=(f"Beat {beat_id} references missing character " f"{character_id}."),
                    suggestion="Add the character bible entry or remove the reference.",
                    entity_type="Character",
                    entity_id=character_id,
                    episode_id=episode_id,
                    scene_id=scene_id,
                    beat_id=beat_id,
                )
                continue

            if not character.visual_prompt_base.strip():
                self._add_issue(
                    issues,
                    severity="warning",
                    category="character_missing_visual_base",
                    message=f"Character {character_id} has no visual prompt base.",
                    suggestion="Add stable appearance and outfit details.",
                    entity_type="Character",
                    entity_id=character_id,
                    episode_id=episode_id,
                    scene_id=scene_id,
                    beat_id=beat_id,
                )
            elif image_prompt and not self._prompt_contains_visual_base(
                image_prompt,
                character.visual_prompt_base,
            ):
                self._add_issue(
                    issues,
                    severity="warning",
                    category="prompt_missing_character_detail",
                    message=(
                        f"Beat {beat_id} prompt omits key visual details for "
                        f"character {character_id}."
                    ),
                    suggestion="Inject the character visual prompt base.",
                    entity_type="Beat",
                    entity_id=beat_id,
                    episode_id=episode_id,
                    scene_id=scene_id,
                    beat_id=beat_id,
                )
            if (
                image_prompt
                and character.default_outfit.strip()
                and not self._prompt_contains_visual_base(
                    image_prompt,
                    character.default_outfit,
                )
            ):
                self._add_issue(
                    issues,
                    severity="warning",
                    category="outfit_continuity",
                    message=(
                        f"Beat {beat_id} prompt omits default outfit for "
                        f"character {character_id}."
                    ),
                    suggestion="Add the character default_outfit to the prompt.",
                    entity_type="Beat",
                    entity_id=beat_id,
                    episode_id=episode_id,
                    scene_id=scene_id,
                    beat_id=beat_id,
                )

        location_id = str(getattr(beat, "location", "") or "").strip()
        if location_id:
            location = locations_by_id.get(location_id)
            if location is None:
                self._add_issue(
                    issues,
                    severity="error",
                    category="broken_reference",
                    message=f"Beat {beat_id} references missing location {location_id}.",
                    suggestion="Add the location bible entry or remove the reference.",
                    entity_type="Location",
                    entity_id=location_id,
                    episode_id=episode_id,
                    scene_id=scene_id,
                    beat_id=beat_id,
                )
            elif not location.visual_prompt_base.strip():
                self._add_issue(
                    issues,
                    severity="warning",
                    category="location_missing_visual_base",
                    message=f"Location {location_id} has no visual prompt base.",
                    suggestion="Add stable setting details.",
                    entity_type="Location",
                    entity_id=location_id,
                    episode_id=episode_id,
                    scene_id=scene_id,
                    beat_id=beat_id,
                )
            elif image_prompt and not self._prompt_contains_visual_base(
                image_prompt,
                location.visual_prompt_base,
            ):
                self._add_issue(
                    issues,
                    severity="warning",
                    category="prompt_missing_location_detail",
                    message=(
                        f"Beat {beat_id} prompt omits key visual details for "
                        f"location {location_id}."
                    ),
                    suggestion="Inject the location visual prompt base.",
                    entity_type="Beat",
                    entity_id=beat_id,
                    episode_id=episode_id,
                    scene_id=scene_id,
                    beat_id=beat_id,
                )
            elif image_prompt:
                missing_context = self._missing_location_context_terms(
                    image_prompt,
                    location,
                )
                if missing_context:
                    self._add_issue(
                        issues,
                        severity="warning",
                        category="location_continuity",
                        message=(
                            f"Beat {beat_id} prompt omits location context: "
                            f"{', '.join(missing_context)}."
                        ),
                        suggestion="Include key lighting or mood details from the location bible.",
                        entity_type="Beat",
                        entity_id=beat_id,
                        episode_id=episode_id,
                        scene_id=scene_id,
                        beat_id=beat_id,
                    )

        if not list(getattr(beat, "continuity_tags", []) or []):
            self._add_issue(
                issues,
                severity="warning",
                category="missing_required_field",
                message=f"Beat {beat_id} has no continuity tags.",
                suggestion="Add tags for character, location, mood, or important objects.",
                entity_type="Beat",
                entity_id=beat_id,
                episode_id=episode_id,
                scene_id=scene_id,
                beat_id=beat_id,
            )

        if review_text and not image_prompt:
            self._add_issue(
                issues,
                severity="warning",
                category="empty_image_prompt",
                message=f"Beat {beat_id} has narration but no image prompt.",
                suggestion="Build an image prompt for this beat.",
                entity_type="Beat",
                entity_id=beat_id,
                episode_id=episode_id,
                scene_id=scene_id,
                beat_id=beat_id,
            )

        if image_prompt and not review_text:
            self._add_issue(
                issues,
                severity="warning",
                category="empty_review_text",
                message=f"Beat {beat_id} has an image prompt but no narration.",
                suggestion="Rewrite review narration for this beat.",
                entity_type="Beat",
                entity_id=beat_id,
                episode_id=episode_id,
                scene_id=scene_id,
                beat_id=beat_id,
            )

        blocked_terms = self._blocked_prompt_terms(image_prompt)
        if blocked_terms:
            self._add_issue(
                issues,
                severity="warning",
                category="product_direction_violation",
                message=(
                    f"Beat {beat_id} image prompt asks for visual text or branding: "
                    f"{', '.join(blocked_terms)}."
                ),
                suggestion="Move those words to negative_prompt unless explicitly needed.",
                entity_type="Beat",
                entity_id=beat_id,
                episode_id=episode_id,
                scene_id=scene_id,
                beat_id=beat_id,
            )

        missing_forbidden_terms = self._missing_style_forbidden_terms(
            project,
            negative_prompt,
        )
        if missing_forbidden_terms:
            self._add_issue(
                issues,
                severity="warning",
                category="product_direction_violation",
                message=(
                    f"Beat {beat_id} negative prompt omits style guard terms: "
                    f"{', '.join(missing_forbidden_terms)}."
                ),
                suggestion="Add the style forbidden terms to negative_prompt.",
                entity_type="Beat",
                entity_id=beat_id,
                episode_id=episode_id,
                scene_id=scene_id,
                beat_id=beat_id,
            )

    def _prompt_contains_visual_base(self, prompt: str, visual_base: str) -> bool:
        prompt_text = prompt.lower()
        terms = self._meaningful_terms(visual_base)
        if not terms:
            return True
        matches = sum(1 for term in terms if term in prompt_text)
        return matches >= min(2, len(terms))

    def _meaningful_terms(self, visual_base: str) -> list[str]:
        words = re.findall(r"[a-zA-Z0-9]+", visual_base.lower())
        terms: list[str] = []
        for word in words:
            if len(word) < 4 or word in self.TERM_STOPWORDS:
                continue
            if word not in terms:
                terms.append(word)
            if len(terms) >= 6:
                break
        return terms

    def _blocked_prompt_terms(self, prompt: str) -> list[str]:
        prompt_text = prompt.lower()
        found: list[str] = []
        for term in self.BLOCKED_PROMPT_TERMS:
            if " " in term:
                if term in prompt_text:
                    found.append(term)
            elif re.search(rf"\b{re.escape(term)}\b", prompt_text):
                found.append(term)
        return found

    def _missing_location_context_terms(
        self,
        prompt: str,
        location: Any,
    ) -> list[str]:
        missing: list[str] = []
        for value in [
            getattr(location, "lighting", ""),
            getattr(location, "mood", ""),
        ]:
            if value and not self._prompt_contains_visual_base(prompt, value):
                missing.append(value)
        return missing

    def _missing_style_forbidden_terms(
        self,
        project: Project,
        negative_prompt: str,
    ) -> list[str]:
        style = self._selected_style_preset(project)
        if not style or not getattr(style, "forbidden_terms", []):
            return []
        lowered_negative = negative_prompt.lower()
        return [
            term for term in style.forbidden_terms if term and term.lower() not in lowered_negative
        ]

    def _selected_style_preset(self, project: Project) -> Any | None:
        if not project.style_presets:
            return None
        preferred = self._normalise_key(project.default_art_style)
        for style in project.style_presets:
            if self._normalise_key(style.style_id) == preferred:
                return style
            if self._normalise_key(style.name) == preferred:
                return style
        return project.style_presets[0]

    def _normalise_key(self, value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")

    def _find_scene(self, project: Project, scene_id: str):
        for episode in project.review_episodes:
            for scene in episode.scenes:
                if scene.scene_id == scene_id:
                    return episode, scene
        raise LookupError(f"Scene not found: {scene_id}")

    def _find_beat(self, project: Project, beat_id: str):
        for episode in project.review_episodes:
            for scene in episode.scenes:
                for beat in scene.beats:
                    if beat.beat_id == beat_id:
                        return episode, scene, beat
        raise LookupError(f"Beat not found: {beat_id}")

    def _add_issue(
        self,
        issues: list[ValidationIssue],
        *,
        severity: str,
        category: str,
        message: str,
        suggestion: str = "",
        entity_type: str = "",
        entity_id: str = "",
        episode_id: str = "",
        scene_id: str = "",
        beat_id: str = "",
    ) -> None:
        issues.append(
            ValidationIssue(
                issue_id=f"cont_{len(issues) + 1:03d}",
                severity=severity,
                category=category,
                message=message,
                suggestion=suggestion,
                entity_type=entity_type,
                entity_id=entity_id,
                episode_id=episode_id,
                scene_id=scene_id,
                beat_id=beat_id,
            )
        )
