"""Offline structural validation for project data."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from app.domain.project import Project
from app.domain.validation import ValidationIssue


class ProjectValidationService:
    def validate_project(self, project: Project) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        self._validate_project_fields(project, issues)
        self._validate_top_level_ids(project, issues)
        self._validate_source_chapters(project, issues)
        self._validate_bible_entries(project, issues)
        self._validate_episodes(project, issues)

        return issues

    def validate_episode(self, project: Project, episode_id: str) -> list[ValidationIssue]:
        issues = self.validate_project(project)
        return [issue for issue in issues if not issue.episode_id or issue.episode_id == episode_id]

    def has_errors(self, issues: list[ValidationIssue]) -> bool:
        return any(issue.severity == "error" for issue in issues)

    def _validate_project_fields(self, project: Project, issues: list[ValidationIssue]) -> None:
        if not self._text(getattr(project, "project_id", "")):
            self._add_issue(
                issues,
                severity="error",
                category="missing_required_field",
                message="Project is missing project_id.",
                suggestion="Assign a stable project_id before saving or exporting.",
                entity_type="Project",
            )

        if not self._text(getattr(project, "title", "")):
            self._add_issue(
                issues,
                severity="error",
                category="missing_required_field",
                message="Project is missing title.",
                suggestion="Add a project title.",
                entity_type="Project",
                entity_id=getattr(project, "project_id", ""),
            )

    def _validate_top_level_ids(self, project: Project, issues: list[ValidationIssue]) -> None:
        self._check_duplicate_ids(
            issues,
            "SourceChapter",
            [getattr(chapter, "chapter_id", "") for chapter in project.source_chapters],
        )
        self._check_duplicate_ids(
            issues,
            "ReviewEpisode",
            [getattr(episode, "episode_id", "") for episode in project.review_episodes],
        )
        self._check_duplicate_ids(
            issues,
            "Character",
            [getattr(character, "character_id", "") for character in project.characters],
        )
        self._check_duplicate_ids(
            issues,
            "Location",
            [getattr(location, "location_id", "") for location in project.locations],
        )
        self._check_duplicate_ids(
            issues,
            "StylePreset",
            [getattr(style_preset, "style_id", "") for style_preset in project.style_presets],
        )

        scene_ids: list[str] = []
        beat_ids: list[str] = []
        for episode in project.review_episodes:
            for scene in self._scenes(episode):
                scene_ids.append(getattr(scene, "scene_id", ""))
                for beat in self._beats(scene):
                    beat_ids.append(getattr(beat, "beat_id", ""))

        self._check_duplicate_ids(issues, "Scene", scene_ids)
        self._check_duplicate_ids(issues, "Beat", beat_ids)

    def _validate_source_chapters(self, project: Project, issues: list[ValidationIssue]) -> None:
        for chapter in project.source_chapters:
            chapter_id = getattr(chapter, "chapter_id", "")
            if not self._text(chapter_id):
                self._add_issue(
                    issues,
                    severity="error",
                    category="missing_required_field",
                    message="A source chapter is missing chapter_id.",
                    suggestion="Assign a stable chapter_id.",
                    entity_type="SourceChapter",
                )
            if not self._text(getattr(chapter, "title", "")):
                self._add_issue(
                    issues,
                    severity="warning",
                    category="missing_required_field",
                    message=f"Source chapter {chapter_id} is missing title.",
                    suggestion="Add a chapter title for readable exports.",
                    entity_type="SourceChapter",
                    entity_id=chapter_id,
                )
            if not self._text(getattr(chapter, "raw_text", "")):
                self._add_issue(
                    issues,
                    severity="error",
                    category="source_raw_text_missing",
                    message=f"Source chapter {chapter_id} has empty raw_text.",
                    suggestion="Import or restore the original chapter text.",
                    entity_type="SourceChapter",
                    entity_id=chapter_id,
                )

    def _validate_bible_entries(self, project: Project, issues: list[ValidationIssue]) -> None:
        for character in project.characters:
            character_id = getattr(character, "character_id", "")
            if not self._text(getattr(character, "visual_prompt_base", "")):
                self._add_issue(
                    issues,
                    severity="warning",
                    category="character_missing_visual_base",
                    message=f"Character {character_id} has no visual prompt base.",
                    suggestion="Add appearance and outfit details for prompt consistency.",
                    entity_type="Character",
                    entity_id=character_id,
                )
            if self._text(getattr(character, "visual_prompt_base", "")) and not self._text(
                getattr(character, "default_outfit", "")
            ):
                self._add_issue(
                    issues,
                    severity="warning",
                    category="missing_required_field",
                    message=f"Character {character_id} has no default outfit.",
                    suggestion="Add default_outfit for long-form visual continuity.",
                    entity_type="Character",
                    entity_id=character_id,
                )

        for location in project.locations:
            location_id = getattr(location, "location_id", "")
            if not self._text(getattr(location, "visual_prompt_base", "")):
                self._add_issue(
                    issues,
                    severity="warning",
                    category="location_missing_visual_base",
                    message=f"Location {location_id} has no visual prompt base.",
                    suggestion="Add stable visual details for the location.",
                    entity_type="Location",
                    entity_id=location_id,
                )

        for style_preset in project.style_presets:
            style_id = getattr(style_preset, "style_id", "")
            if not self._text(getattr(style_preset, "positive_prompt", "")):
                self._add_issue(
                    issues,
                    severity="warning",
                    category="missing_required_field",
                    message=f"Style preset {style_id} has no positive prompt.",
                    suggestion="Add positive_prompt so prompts have a stable art style.",
                    entity_type="StylePreset",
                    entity_id=style_id,
                )

    def _validate_episodes(self, project: Project, issues: list[ValidationIssue]) -> None:
        chapter_ids = {getattr(chapter, "chapter_id", "") for chapter in project.source_chapters}

        for episode in project.review_episodes:
            episode_id = getattr(episode, "episode_id", "")
            if not self._text(episode_id):
                self._add_issue(
                    issues,
                    severity="error",
                    category="missing_required_field",
                    message="A review episode is missing episode_id.",
                    suggestion="Assign a stable episode_id.",
                    entity_type="ReviewEpisode",
                )

            if not self._text(getattr(episode, "title", "")):
                self._add_issue(
                    issues,
                    severity="warning",
                    category="missing_required_field",
                    message=f"Review episode {episode_id} is missing title.",
                    suggestion="Add an episode title.",
                    entity_type="ReviewEpisode",
                    entity_id=episode_id,
                    episode_id=episode_id,
                )

            for chapter_id in self._list(getattr(episode, "source_chapter_ids", [])):
                if chapter_id not in chapter_ids:
                    self._add_issue(
                        issues,
                        severity="error",
                        category="broken_reference",
                        message=(
                            f"Episode {episode_id} references missing source "
                            f"chapter {chapter_id}."
                        ),
                        suggestion="Remove the reference or add the source chapter.",
                        entity_type="ReviewEpisode",
                        entity_id=episode_id,
                        episode_id=episode_id,
                    )

            scenes = self._scenes(episode)
            scene_ids = [getattr(scene, "scene_id", "") for scene in scenes]
            declared_scene_ids = self._list(getattr(episode, "scene_ids", scene_ids))

            if not scene_ids:
                self._add_issue(
                    issues,
                    severity="warning",
                    category="episode_without_scenes",
                    message=f"Episode {episode_id} has no scenes.",
                    suggestion="Plan scenes before generating beats or exporting.",
                    entity_type="ReviewEpisode",
                    entity_id=episode_id,
                    episode_id=episode_id,
                )

            for scene_id in declared_scene_ids:
                if scene_id not in scene_ids:
                    self._add_issue(
                        issues,
                        severity="error",
                        category="broken_reference",
                        message=(f"Episode {episode_id} references missing scene " f"{scene_id}."),
                        suggestion="Remove the stale scene reference or restore the scene.",
                        entity_type="Scene",
                        entity_id=scene_id,
                        episode_id=episode_id,
                        scene_id=scene_id,
                    )

            for scene in scenes:
                self._validate_scene(project, episode, scene, issues)

    def _validate_scene(
        self,
        project: Project,
        episode: Any,
        scene: Any,
        issues: list[ValidationIssue],
    ) -> None:
        episode_id = getattr(episode, "episode_id", "")
        scene_id = getattr(scene, "scene_id", "")
        if not self._text(scene_id):
            self._add_issue(
                issues,
                severity="error",
                category="missing_required_field",
                message=f"A scene in episode {episode_id} is missing scene_id.",
                suggestion="Assign a stable scene_id.",
                entity_type="Scene",
                episode_id=episode_id,
            )

        if getattr(scene, "episode_id", episode_id) != episode_id:
            self._add_issue(
                issues,
                severity="error",
                category="broken_reference",
                message=(
                    f"Scene {scene_id} belongs to {getattr(scene, 'episode_id', '')}, "
                    f"not episode {episode_id}."
                ),
                suggestion="Move the scene or correct its episode_id.",
                entity_type="Scene",
                entity_id=scene_id,
                episode_id=episode_id,
                scene_id=scene_id,
            )

        if not self._text(getattr(scene, "title", "")):
            self._add_issue(
                issues,
                severity="warning",
                category="missing_required_field",
                message=f"Scene {scene_id} is missing title.",
                suggestion="Add a scene title for readable exports.",
                entity_type="Scene",
                entity_id=scene_id,
                episode_id=episode_id,
                scene_id=scene_id,
            )

        beats = self._beats(scene)
        beat_ids = [getattr(beat, "beat_id", "") for beat in beats]
        declared_beat_ids = self._list(getattr(scene, "beat_ids", beat_ids))

        if not beat_ids:
            self._add_issue(
                issues,
                severity="warning",
                category="scene_without_beats",
                message=f"Scene {scene_id} has no beats.",
                suggestion="Generate or add beats for this scene.",
                entity_type="Scene",
                entity_id=scene_id,
                episode_id=episode_id,
                scene_id=scene_id,
            )

        for beat_id in declared_beat_ids:
            if beat_id not in beat_ids:
                self._add_issue(
                    issues,
                    severity="error",
                    category="broken_reference",
                    message=f"Scene {scene_id} references missing beat {beat_id}.",
                    suggestion="Remove the stale beat reference or restore the beat.",
                    entity_type="Beat",
                    entity_id=beat_id,
                    episode_id=episode_id,
                    scene_id=scene_id,
                    beat_id=beat_id,
                )

        self._validate_beat_order(episode_id, scene_id, beats, issues)

        for beat in beats:
            self._validate_beat(project, episode_id, scene_id, beat, issues)

    def _validate_beat(
        self,
        project: Project,
        episode_id: str,
        scene_id: str,
        beat: Any,
        issues: list[ValidationIssue],
    ) -> None:
        beat_id = getattr(beat, "beat_id", "")
        if not self._text(beat_id):
            self._add_issue(
                issues,
                severity="error",
                category="missing_required_field",
                message=f"A beat in scene {scene_id} is missing beat_id.",
                suggestion="Assign a stable beat_id.",
                entity_type="Beat",
                episode_id=episode_id,
                scene_id=scene_id,
            )

        if getattr(beat, "scene_id", scene_id) != scene_id:
            self._add_issue(
                issues,
                severity="error",
                category="broken_reference",
                message=(
                    f"Beat {beat_id} belongs to {getattr(beat, 'scene_id', '')}, "
                    f"not scene {scene_id}."
                ),
                suggestion="Move the beat or correct its scene_id.",
                entity_type="Beat",
                entity_id=beat_id,
                episode_id=episode_id,
                scene_id=scene_id,
                beat_id=beat_id,
            )

        if int(getattr(beat, "order_index", 0) or 0) <= 0:
            self._add_issue(
                issues,
                severity="warning",
                category="beat_order_issue",
                message=f"Beat {beat_id} has invalid order_index.",
                suggestion="Use a positive order_index within the scene.",
                entity_type="Beat",
                entity_id=beat_id,
                episode_id=episode_id,
                scene_id=scene_id,
                beat_id=beat_id,
            )

        if not self._text(getattr(beat, "review_text", "")):
            self._add_issue(
                issues,
                severity="warning",
                category="empty_review_text",
                message=f"Beat {beat_id} has no review narration.",
                suggestion="Run review rewriting before final export.",
                entity_type="Beat",
                entity_id=beat_id,
                episode_id=episode_id,
                scene_id=scene_id,
                beat_id=beat_id,
            )

        if self._text(getattr(beat, "review_text", "")) and not self._text(
            getattr(beat, "image_prompt", "")
        ):
            self._add_issue(
                issues,
                severity="warning",
                category="empty_image_prompt",
                message=f"Beat {beat_id} has review narration but no image prompt.",
                suggestion="Build image prompts before exporting prompt lists.",
                entity_type="Beat",
                entity_id=beat_id,
                episode_id=episode_id,
                scene_id=scene_id,
                beat_id=beat_id,
            )

        if self._text(getattr(beat, "image_prompt", "")) and not self._text(
            getattr(beat, "negative_prompt", "")
        ):
            self._add_issue(
                issues,
                severity="warning",
                category="empty_negative_prompt",
                message=f"Beat {beat_id} has no negative prompt.",
                suggestion="Add a negative prompt for image consistency.",
                entity_type="Beat",
                entity_id=beat_id,
                episode_id=episode_id,
                scene_id=scene_id,
                beat_id=beat_id,
            )

    def _validate_beat_order(
        self,
        episode_id: str,
        scene_id: str,
        beats: list[Any],
        issues: list[ValidationIssue],
    ) -> None:
        order_indexes = [int(getattr(beat, "order_index", 0) or 0) for beat in beats]
        duplicate_orders = [order for order, count in Counter(order_indexes).items() if count > 1]
        for order_index in duplicate_orders:
            self._add_issue(
                issues,
                severity="error",
                category="beat_order_issue",
                message=(f"Scene {scene_id} has duplicate beat order_index " f"{order_index}."),
                suggestion="Give each beat a unique order_index in the scene.",
                entity_type="Scene",
                entity_id=scene_id,
                episode_id=episode_id,
                scene_id=scene_id,
            )

        positive_orders = sorted(order for order in order_indexes if order > 0)
        expected_orders = list(range(1, len(positive_orders) + 1))
        if positive_orders and positive_orders != expected_orders:
            self._add_issue(
                issues,
                severity="warning",
                category="beat_order_issue",
                message=f"Scene {scene_id} beat order has gaps or starts late.",
                suggestion="Use consecutive order_index values for clearer exports.",
                entity_type="Scene",
                entity_id=scene_id,
                episode_id=episode_id,
                scene_id=scene_id,
            )

    def _check_duplicate_ids(
        self,
        issues: list[ValidationIssue],
        entity_type: str,
        ids: Iterable[str],
    ) -> None:
        id_counts = Counter(item_id for item_id in ids if self._text(item_id))
        for item_id, count in sorted(id_counts.items()):
            if count > 1:
                self._add_issue(
                    issues,
                    severity="error",
                    category="duplicate_id",
                    message=f"{entity_type} id {item_id} appears {count} times.",
                    suggestion="Keep IDs unique within each entity type.",
                    entity_type=entity_type,
                    entity_id=item_id,
                )

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
                issue_id=f"val_{len(issues) + 1:03d}",
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

    def _scenes(self, episode: Any) -> list[Any]:
        return list(getattr(episode, "scenes", []) or [])

    def _beats(self, scene: Any) -> list[Any]:
        ordered_beats = getattr(scene, "ordered_beats", None)
        if callable(ordered_beats):
            return list(ordered_beats())
        return sorted(
            list(getattr(scene, "beats", []) or []),
            key=lambda beat: int(getattr(beat, "order_index", 0) or 0),
        )

    def _list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value else []
        return [str(item) for item in value if self._text(str(item))]

    def _text(self, value: Any) -> bool:
        return bool(str(value).strip()) if value is not None else False
