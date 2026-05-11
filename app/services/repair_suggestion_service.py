"""Assisted repair suggestions and explicit scoped fixes."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from app.domain.beat import Beat
from app.domain.character import Character
from app.domain.location import Location
from app.domain.project import Project
from app.domain.repair import RepairAction, RepairResult
from app.domain.scene import Scene
from app.services.beat_generator_service import BeatGeneratorService
from app.services.bible_service import BibleService
from app.services.continuity_checker_service import ContinuityCheckerService
from app.services.production_readiness_service import ProductionReadinessService
from app.services.project_service import ProjectService
from app.services.project_validation_service import ProjectValidationService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.prompt_quality_service import PromptQualityService
from app.services.review_quality_service import ReviewQualityService
from app.services.review_rewriter_service import ReviewRewriterService


class RepairSuggestionService:
    def __init__(
        self,
        project_service: ProjectService | None = None,
        validation_service: ProjectValidationService | None = None,
        continuity_checker: ContinuityCheckerService | None = None,
        review_quality_service: ReviewQualityService | None = None,
        prompt_quality_service: PromptQualityService | None = None,
        readiness_service: ProductionReadinessService | None = None,
        prompt_builder_service: PromptBuilderService | None = None,
        review_rewriter_service: ReviewRewriterService | None = None,
        beat_generator_service: BeatGeneratorService | None = None,
        bible_service: BibleService | None = None,
    ) -> None:
        self.project_service = project_service or ProjectService()
        self.validation_service = validation_service or ProjectValidationService()
        self.continuity_checker = continuity_checker or ContinuityCheckerService(
            self.project_service
        )
        self.review_quality_service = review_quality_service or ReviewQualityService(
            self.project_service
        )
        self.prompt_quality_service = prompt_quality_service or PromptQualityService(
            self.project_service
        )
        self.readiness_service = readiness_service or ProductionReadinessService(
            self.project_service
        )
        self.prompt_builder_service = prompt_builder_service or PromptBuilderService()
        self.review_rewriter_service = review_rewriter_service or ReviewRewriterService()
        self.beat_generator_service = beat_generator_service or BeatGeneratorService(
            self.project_service
        )
        self.bible_service = bible_service or BibleService()

    def suggest_repairs_for_episode(
        self,
        project: Project,
        episode_id: str,
    ) -> list[RepairAction]:
        actions_by_key: dict[tuple[str, str, str, str], RepairAction] = {}
        validation_issues = self.validation_service.validate_episode(project, episode_id)
        continuity_issues = self.continuity_checker.check_episode(project, episode_id)
        review_report = self.review_quality_service.build_episode_report(
            project,
            episode_id,
        )
        prompt_report = self.prompt_quality_service.build_episode_report(
            project,
            episode_id,
        )
        readiness_report = self.readiness_service.build_episode_report(
            project,
            episode_id,
        )

        for issue in [*validation_issues, *continuity_issues]:
            self._add_actions_for_issue(project, actions_by_key, self._issue_data(issue))

        for result in review_report.get("results", []):
            for issue in result.get("issues", []):
                issue_data = dict(issue)
                issue_data["episode_id"] = episode_id
                issue_data["beat_id"] = result.get("beat_id", "")
                issue_data["issue_id"] = (
                    f"review_{result.get('beat_id', '')}_{issue.get('category', '')}"
                )
                self._add_actions_for_issue(project, actions_by_key, issue_data)

        for result in prompt_report.get("results", []):
            for issue in result.get("issues", []):
                issue_data = dict(issue)
                issue_data["episode_id"] = episode_id
                issue_data["beat_id"] = result.get("beat_id", "")
                issue_data["issue_id"] = (
                    f"prompt_{result.get('beat_id', '')}_{issue.get('category', '')}"
                )
                self._add_actions_for_issue(project, actions_by_key, issue_data)

        self._add_style_repair_if_needed(project, actions_by_key)
        if readiness_report.status == "blocked":
            self._add_validate_again_action(
                actions_by_key,
                episode_id=episode_id,
                source_issue_id=f"readiness_{episode_id}",
            )

        return self._renumber_actions(actions_by_key.values())

    def suggest_repairs_for_project(self, project: Project) -> list[RepairAction]:
        actions_by_key: dict[tuple[str, str, str, str], RepairAction] = {}
        for issue in self.validation_service.validate_project(project):
            self._add_actions_for_issue(project, actions_by_key, self._issue_data(issue))
        self._add_style_repair_if_needed(project, actions_by_key)
        for episode in project.review_episodes:
            for action in self.suggest_repairs_for_episode(project, episode.episode_id):
                self._merge_action(actions_by_key, action)
        return self._renumber_actions(actions_by_key.values())

    def apply_repair_action(
        self,
        project: Project,
        action_id: str,
        actions: list[RepairAction],
        allow_medium_risk: bool = False,
        allow_high_risk: bool = False,
    ) -> RepairResult:
        action = self._find_action(action_id, actions)
        permission_result = self._permission_result(
            action,
            allow_medium_risk=allow_medium_risk,
            allow_high_risk=allow_high_risk,
        )
        if permission_result is not None:
            return permission_result

        if action.action_type == "rebuild_image_prompt":
            return self._apply_rebuild_image_prompt(project, action)
        if action.action_type == "add_negative_prompt":
            return self._apply_add_negative_prompt(project, action)
        if action.action_type == "rewrite_review_text":
            return self._apply_rewrite_review_text(project, action)
        if action.action_type == "create_default_style_presets":
            return self._apply_create_default_style_presets(project, action)
        if action.action_type == "generate_missing_beats":
            return self._apply_generate_missing_beats(project, action)
        if action.action_type == "update_character_bible":
            return self._apply_update_character_bible(project, action)
        if action.action_type == "update_location_bible":
            return self._apply_update_location_bible(project, action)

        return RepairResult(
            action_id=action.action_id,
            applied=False,
            message=f"No safe auto-fix is available for {action.action_type}.",
            changed_entity_type=action.target_entity_type,
            changed_entity_id=action.target_entity_id,
        )

    def apply_low_risk_repairs(
        self,
        project: Project,
        actions: list[RepairAction],
    ) -> list[RepairResult]:
        results: list[RepairResult] = []
        for action in actions:
            if action.risk_level == "low" and action.can_auto_apply:
                results.append(
                    self.apply_repair_action(project, action.action_id, actions)
                )
        return results

    def _add_actions_for_issue(
        self,
        project: Project,
        actions_by_key: dict[tuple[str, str, str, str], RepairAction],
        issue: dict[str, Any],
    ) -> None:
        category = str(issue.get("category", ""))
        if category in {"empty_review_text", "missing_review_text"}:
            self._merge_action(
                actions_by_key,
                self._beat_action(
                    issue,
                    action_type="rewrite_review_text",
                    title="Rewrite missing review narration",
                    description="Generate deterministic review narration for this beat.",
                    risk_level="low",
                    can_auto_apply=True,
                ),
            )
        elif category in {"too_short", "generic_summary"} and str(issue.get("issue_id", "")).startswith("review_"):
            self._merge_action(
                actions_by_key,
                self._beat_action(
                    issue,
                    action_type="rewrite_review_text",
                    title="Rewrite weak review narration",
                    description="Regenerate the existing low-scoring review narration.",
                    risk_level="medium",
                    can_auto_apply=True,
                    requires_user_review=True,
                ),
            )
        elif category in {"empty_image_prompt", "missing_prompt"}:
            self._merge_action(
                actions_by_key,
                self._beat_action(
                    issue,
                    action_type="rebuild_image_prompt",
                    title="Rebuild missing image prompt",
                    description="Build image and negative prompts from beat, scene, bible, and style data.",
                    risk_level="low",
                    can_auto_apply=True,
                ),
            )
        elif category in {"empty_negative_prompt", "weak_negative_prompt"}:
            self._merge_action(
                actions_by_key,
                self._beat_action(
                    issue,
                    action_type="add_negative_prompt",
                    title="Add or rebuild negative prompt",
                    description="Build a deterministic negative prompt while preserving narration.",
                    risk_level="low",
                    can_auto_apply=True,
                ),
            )
        elif category in {"missing_style"}:
            self._merge_action(
                actions_by_key,
                self._project_action(
                    issue,
                    action_type="create_default_style_presets",
                    title="Create default style presets",
                    description="Add reusable professional style presets for prompt consistency.",
                    risk_level="low",
                    can_auto_apply=True,
                ),
            )
            if issue.get("beat_id"):
                self._merge_action(
                    actions_by_key,
                    self._beat_action(
                        issue,
                        action_type="rebuild_image_prompt",
                        title="Rebuild prompt with style context",
                        description="Rebuild this prompt after style data is available.",
                        risk_level="low",
                        can_auto_apply=True,
                    ),
                )
        elif category in {
            "missing_character_detail",
            "missing_outfit",
            "outfit_continuity",
            "prompt_missing_character_detail",
        }:
            self._merge_action(
                actions_by_key,
                self._beat_action(
                    issue,
                    action_type="rebuild_image_prompt",
                    title="Rebuild prompt with character details",
                    description="Rebuild the beat prompt using Character Bible details.",
                    risk_level="low",
                    can_auto_apply=True,
                ),
            )
        elif category == "character_missing_visual_base":
            character_id = self._target_entity_id(issue)
            self._merge_action(
                actions_by_key,
                self._bible_action(
                    project,
                    issue,
                    action_type="update_character_bible",
                    entity_type="Character",
                    entity_id=character_id,
                    title="Update Character Bible visual base",
                    description="Add a placeholder visual prompt base for this character.",
                    suggested_changes=self._character_placeholder(project, character_id),
                ),
            )
        elif category in {
            "missing_location_detail",
            "prompt_missing_location_detail",
            "location_continuity",
        }:
            self._merge_action(
                actions_by_key,
                self._beat_action(
                    issue,
                    action_type="rebuild_image_prompt",
                    title="Rebuild prompt with location details",
                    description="Rebuild the beat prompt using Location Bible details.",
                    risk_level="low",
                    can_auto_apply=True,
                ),
            )
        elif category == "location_missing_visual_base":
            location_id = self._target_entity_id(issue)
            self._merge_action(
                actions_by_key,
                self._bible_action(
                    project,
                    issue,
                    action_type="update_location_bible",
                    entity_type="Location",
                    entity_id=location_id,
                    title="Update Location Bible visual base",
                    description="Add a placeholder visual prompt base for this location.",
                    suggested_changes=self._location_placeholder(project, location_id),
                ),
            )
        elif category == "scene_without_beats":
            self._merge_action(
                actions_by_key,
                RepairAction(
                    action_id="",
                    action_type="generate_missing_beats",
                    severity=str(issue.get("severity", "warning")),
                    title="Generate missing beats",
                    description="Generate deterministic planned beats for this empty scene.",
                    target_entity_type="Scene",
                    target_entity_id=str(issue.get("scene_id") or issue.get("entity_id", "")),
                    episode_id=str(issue.get("episode_id", "")),
                    scene_id=str(issue.get("scene_id") or issue.get("entity_id", "")),
                    source_issue_ids=[self._source_issue_id(issue)],
                    suggested_changes={"service": "BeatGeneratorService"},
                    can_auto_apply=True,
                    requires_user_review=True,
                    risk_level="medium",
                ),
            )
        elif category in {"broken_reference", "duplicate_id", "beat_order_issue"}:
            self._merge_action(
                actions_by_key,
                RepairAction(
                    action_id="",
                    action_type="no_safe_auto_fix",
                    severity=str(issue.get("severity", "error")),
                    title="Manual repair required",
                    description=str(issue.get("message") or "This issue needs manual inspection."),
                    target_entity_type=str(issue.get("entity_type", "")),
                    target_entity_id=self._target_entity_id(issue),
                    episode_id=str(issue.get("episode_id", "")),
                    scene_id=str(issue.get("scene_id", "")),
                    beat_id=str(issue.get("beat_id", "")),
                    source_issue_ids=[self._source_issue_id(issue)],
                    suggested_changes={"reason": "broken or ambiguous reference"},
                    can_auto_apply=False,
                    requires_user_review=True,
                    risk_level="high",
                ),
            )

    def _add_style_repair_if_needed(
        self,
        project: Project,
        actions_by_key: dict[tuple[str, str, str, str], RepairAction],
    ) -> None:
        if project.style_presets and any(
            style.positive_prompt.strip() for style in project.style_presets
        ):
            return
        self._merge_action(
            actions_by_key,
            RepairAction(
                action_id="",
                action_type="create_default_style_presets",
                severity="warning",
                title="Create default style presets",
                description="Project has no usable style preset for stable image prompts.",
                target_entity_type="Project",
                target_entity_id=project.project_id,
                source_issue_ids=["style_presets_missing"],
                suggested_changes={"preset_count": 8},
                can_auto_apply=True,
                risk_level="low",
            ),
        )

    def _add_validate_again_action(
        self,
        actions_by_key: dict[tuple[str, str, str, str], RepairAction],
        *,
        episode_id: str,
        source_issue_id: str,
    ) -> None:
        self._merge_action(
            actions_by_key,
            RepairAction(
                action_id="",
                action_type="validate_again",
                severity="info",
                title="Run validation again after repair",
                description="Re-run validation and readiness after applying selected repairs.",
                target_entity_type="ReviewEpisode",
                target_entity_id=episode_id,
                episode_id=episode_id,
                source_issue_ids=[source_issue_id],
                can_auto_apply=False,
                risk_level="low",
            ),
        )

    def _apply_rebuild_image_prompt(
        self,
        project: Project,
        action: RepairAction,
    ) -> RepairResult:
        beat = self._find_beat(project, action.beat_id)
        before = beat.to_dict()
        self.prompt_builder_service.build_prompt_for_beat(project, beat.beat_id)
        return self._applied_result(action, "Rebuilt image prompt.", before, beat.to_dict())

    def _apply_add_negative_prompt(
        self,
        project: Project,
        action: RepairAction,
    ) -> RepairResult:
        beat = self._find_beat(project, action.beat_id)
        before = beat.to_dict()
        old_image_prompt = beat.image_prompt
        self.prompt_builder_service.build_prompt_for_beat(project, beat.beat_id)
        if old_image_prompt.strip():
            beat.image_prompt = old_image_prompt
        return self._applied_result(action, "Added negative prompt.", before, beat.to_dict())

    def _apply_rewrite_review_text(
        self,
        project: Project,
        action: RepairAction,
    ) -> RepairResult:
        beat = self._find_beat(project, action.beat_id)
        before = beat.to_dict()
        self.review_rewriter_service.rewrite_beat(project, beat.beat_id)
        return self._applied_result(action, "Rewrote review narration.", before, beat.to_dict())

    def _apply_create_default_style_presets(
        self,
        project: Project,
        action: RepairAction,
    ) -> RepairResult:
        before = {"style_presets": [style.to_dict() for style in project.style_presets]}
        self.bible_service.create_default_style_presets(project)
        after = {"style_presets": [style.to_dict() for style in project.style_presets]}
        return self._applied_result(action, "Created default style presets.", before, after)

    def _apply_generate_missing_beats(
        self,
        project: Project,
        action: RepairAction,
    ) -> RepairResult:
        scene = self._find_scene(project, action.scene_id)
        before = scene.to_dict()
        self.beat_generator_service.generate_beats_for_scene(
            project,
            action.episode_id,
            action.scene_id,
        )
        return self._applied_result(action, "Generated missing beats.", before, scene.to_dict())

    def _apply_update_character_bible(
        self,
        project: Project,
        action: RepairAction,
    ) -> RepairResult:
        character = self._find_character(project, action.target_entity_id)
        if character is None:
            return RepairResult(
                action_id=action.action_id,
                applied=False,
                message="Character not found.",
                changed_entity_type="Character",
                changed_entity_id=action.target_entity_id,
            )
        before = character.to_dict()
        updated = replace(
            character,
            visual_prompt_base=action.suggested_changes.get(
                "visual_prompt_base",
                character.visual_prompt_base,
            ),
        )
        self.bible_service.add_or_update_character(project, updated)
        return self._applied_result(action, "Updated character visual base.", before, updated.to_dict())

    def _apply_update_location_bible(
        self,
        project: Project,
        action: RepairAction,
    ) -> RepairResult:
        location = self._find_location(project, action.target_entity_id)
        if location is None:
            return RepairResult(
                action_id=action.action_id,
                applied=False,
                message="Location not found.",
                changed_entity_type="Location",
                changed_entity_id=action.target_entity_id,
            )
        before = location.to_dict()
        updated = replace(
            location,
            visual_prompt_base=action.suggested_changes.get(
                "visual_prompt_base",
                location.visual_prompt_base,
            ),
        )
        self.bible_service.add_or_update_location(project, updated)
        return self._applied_result(action, "Updated location visual base.", before, updated.to_dict())

    def _permission_result(
        self,
        action: RepairAction,
        *,
        allow_medium_risk: bool,
        allow_high_risk: bool,
    ) -> RepairResult | None:
        if not action.can_auto_apply:
            return RepairResult(
                action_id=action.action_id,
                applied=False,
                message=f"Action {action.action_type} has no safe automatic repair.",
                changed_entity_type=action.target_entity_type,
                changed_entity_id=action.target_entity_id,
            )
        if action.risk_level == "medium" and not allow_medium_risk:
            return RepairResult(
                action_id=action.action_id,
                applied=False,
                message="Medium-risk repair requires allow_medium_risk=True.",
                changed_entity_type=action.target_entity_type,
                changed_entity_id=action.target_entity_id,
            )
        if action.risk_level == "high" and not allow_high_risk:
            return RepairResult(
                action_id=action.action_id,
                applied=False,
                message="High-risk repair requires allow_high_risk=True.",
                changed_entity_type=action.target_entity_type,
                changed_entity_id=action.target_entity_id,
            )
        return None

    def _applied_result(
        self,
        action: RepairAction,
        message: str,
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> RepairResult:
        return RepairResult(
            action_id=action.action_id,
            applied=True,
            message=message,
            changed_entity_type=action.target_entity_type,
            changed_entity_id=action.target_entity_id,
            before_snapshot=before,
            after_snapshot=after,
        )

    def _beat_action(
        self,
        issue: dict[str, Any],
        *,
        action_type: str,
        title: str,
        description: str,
        risk_level: str,
        can_auto_apply: bool,
        requires_user_review: bool = False,
    ) -> RepairAction:
        beat_id = str(issue.get("beat_id") or issue.get("entity_id", ""))
        return RepairAction(
            action_id="",
            action_type=action_type,
            severity=str(issue.get("severity", "warning")),
            title=title,
            description=description,
            target_entity_type="Beat",
            target_entity_id=beat_id,
            episode_id=str(issue.get("episode_id", "")),
            scene_id=str(issue.get("scene_id", "")),
            beat_id=beat_id,
            source_issue_ids=[self._source_issue_id(issue)],
            suggested_changes={"service": self._service_name_for_action(action_type)},
            can_auto_apply=can_auto_apply,
            requires_user_review=requires_user_review,
            risk_level=risk_level,
        )

    def _project_action(
        self,
        issue: dict[str, Any],
        *,
        action_type: str,
        title: str,
        description: str,
        risk_level: str,
        can_auto_apply: bool,
    ) -> RepairAction:
        return RepairAction(
            action_id="",
            action_type=action_type,
            severity=str(issue.get("severity", "warning")),
            title=title,
            description=description,
            target_entity_type="Project",
            target_entity_id=str(issue.get("project_id", "")),
            episode_id=str(issue.get("episode_id", "")),
            source_issue_ids=[self._source_issue_id(issue)],
            suggested_changes={"service": "BibleService"},
            can_auto_apply=can_auto_apply,
            risk_level=risk_level,
        )

    def _bible_action(
        self,
        project: Project,
        issue: dict[str, Any],
        *,
        action_type: str,
        entity_type: str,
        entity_id: str,
        title: str,
        description: str,
        suggested_changes: dict[str, Any],
    ) -> RepairAction:
        del project
        return RepairAction(
            action_id="",
            action_type=action_type,
            severity=str(issue.get("severity", "warning")),
            title=title,
            description=description,
            target_entity_type=entity_type,
            target_entity_id=entity_id,
            episode_id=str(issue.get("episode_id", "")),
            scene_id=str(issue.get("scene_id", "")),
            beat_id=str(issue.get("beat_id", "")),
            source_issue_ids=[self._source_issue_id(issue)],
            suggested_changes=suggested_changes,
            can_auto_apply=True,
            requires_user_review=True,
            risk_level="medium",
        )

    def _merge_action(
        self,
        actions_by_key: dict[tuple[str, str, str, str], RepairAction],
        action: RepairAction,
    ) -> None:
        key = (
            action.action_type,
            action.target_entity_type,
            action.target_entity_id,
            action.beat_id or action.scene_id or action.episode_id,
        )
        existing = actions_by_key.get(key)
        if existing is None:
            actions_by_key[key] = action
            return
        existing.source_issue_ids = list(
            dict.fromkeys([*existing.source_issue_ids, *action.source_issue_ids])
        )
        existing.suggested_changes.update(action.suggested_changes)

    def _renumber_actions(self, actions: Any) -> list[RepairAction]:
        numbered: list[RepairAction] = []
        for index, action in enumerate(actions, start=1):
            numbered.append(replace(action, action_id=f"action_{index:03d}"))
        return numbered

    def _issue_data(self, issue: Any) -> dict[str, Any]:
        return issue.to_dict() if hasattr(issue, "to_dict") else dict(issue)

    def _source_issue_id(self, issue: dict[str, Any]) -> str:
        return str(issue.get("issue_id") or f"{issue.get('category', 'issue')}_{issue.get('beat_id') or issue.get('entity_id', '')}")

    def _target_entity_id(self, issue: dict[str, Any]) -> str:
        return str(
            issue.get("entity_id")
            or issue.get("beat_id")
            or issue.get("scene_id")
            or issue.get("episode_id")
            or ""
        )

    def _character_placeholder(
        self,
        project: Project,
        character_id: str,
    ) -> dict[str, Any]:
        character = self._find_character(project, character_id)
        if character is None:
            return {"visual_prompt_base": f"{character_id}, consistent appearance"}
        pieces = [
            character.appearance,
            character.hair,
            character.eyes,
            character.default_outfit,
            character.name,
        ]
        value = ", ".join(piece for piece in pieces if piece.strip())
        return {"visual_prompt_base": value or f"{character.name}, consistent appearance"}

    def _location_placeholder(
        self,
        project: Project,
        location_id: str,
    ) -> dict[str, Any]:
        location = self._find_location(project, location_id)
        if location is None:
            return {"visual_prompt_base": f"{location_id}, consistent setting"}
        pieces = [
            location.description,
            location.mood,
            location.lighting,
            location.name,
        ]
        value = ", ".join(piece for piece in pieces if piece.strip())
        return {"visual_prompt_base": value or f"{location.name}, consistent setting"}

    def _service_name_for_action(self, action_type: str) -> str:
        if action_type == "rewrite_review_text":
            return "ReviewRewriterService"
        if action_type in {"rebuild_image_prompt", "add_negative_prompt"}:
            return "PromptBuilderService"
        return ""

    def _find_action(self, action_id: str, actions: list[RepairAction]) -> RepairAction:
        for action in actions:
            if action.action_id == action_id:
                return action
        raise LookupError(f"RepairAction not found: {action_id}")

    def _find_beat(self, project: Project, beat_id: str) -> Beat:
        for episode in project.review_episodes:
            for scene in episode.scenes:
                for beat in scene.beats:
                    if beat.beat_id == beat_id:
                        return beat
        raise LookupError(f"Beat not found: {beat_id}")

    def _find_scene(self, project: Project, scene_id: str) -> Scene:
        for episode in project.review_episodes:
            for scene in episode.scenes:
                if scene.scene_id == scene_id:
                    return scene
        raise LookupError(f"Scene not found: {scene_id}")

    def _find_character(self, project: Project, character_id: str) -> Character | None:
        for character in project.characters:
            if character.character_id == character_id:
                return character
        return None

    def _find_location(self, project: Project, location_id: str) -> Location | None:
        for location in project.locations:
            if location.location_id == location_id:
                return location
        return None
