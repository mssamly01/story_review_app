"""Controller for batch project workflows."""

from __future__ import annotations

from pathlib import Path

from app.domain.episode import ReviewEpisode
from app.domain.project import Project
from app.domain.validation import ValidationIssue
from app.infrastructure.ai_gateway import AIGateway
from app.infrastructure.ai_gateway_factory import create_ai_gateway
from app.services.batch_workflow_service import BatchWorkflowService
from app.services.project_service import ProjectService


class BatchWorkflowController:
    def __init__(self, project_service: ProjectService | None = None) -> None:
        self.project_service = project_service or ProjectService()
        self.last_validation_issues: dict[str, list[ValidationIssue]] = {}

    def plan_episodes_from_chapters(
        self,
        project: Project,
        *,
        chapter_ids: list[str],
        chapters_per_episode: int = 1,
        tone: str | None = None,
        density: str | None = None,
        ai_mode: str = "deterministic",
        model: str | None = None,
    ) -> list[ReviewEpisode]:
        gateway = self._gateway_for_mode(ai_mode, model)
        return BatchWorkflowService(
            self.project_service,
            ai_gateway=gateway,
        ).plan_episodes_from_chapters(
            project,
            chapter_ids,
            chapters_per_episode=chapters_per_episode,
            tone=tone,
            density=density,
            use_ai=gateway is not None,
        )

    def run_generation_for_episodes(
        self,
        project: Project,
        *,
        episode_ids: list[str],
        tone: str | None = None,
        density: str | None = None,
        style_preset_id: str | None = None,
        validate: bool = False,
        fail_on_validation_error: bool = False,
        ai_mode: str = "deterministic",
        model: str | None = None,
    ) -> list[ReviewEpisode]:
        gateway = self._gateway_for_mode(ai_mode, model)
        service = BatchWorkflowService(
            self.project_service,
            ai_gateway=gateway,
        )
        episodes = service.run_generation_for_episodes(
            project,
            episode_ids,
            tone=tone,
            density=density,
            style_preset_id=style_preset_id,
            use_ai=gateway is not None,
            validate=validate,
            fail_on_validation_error=fail_on_validation_error,
        )
        self.last_validation_issues = service.last_validation_issues
        return episodes

    def export_episodes(
        self,
        project: Project,
        *,
        episode_ids: list[str],
        output_dir: str | Path,
        formats: list[str],
    ) -> list[Path]:
        return BatchWorkflowService(self.project_service).export_episodes(
            project,
            episode_ids,
            output_dir,
            formats,
        )

    def _gateway_for_mode(self, ai_mode: str, model: str | None) -> AIGateway | None:
        if ai_mode == "deterministic":
            return None
        if ai_mode == "mock":
            return create_ai_gateway(True, mock_ai=True, model=model)
        if ai_mode == "real":
            return create_ai_gateway(True, real_ai=True, model=model)
        raise ValueError(f"Unsupported AI mode: {ai_mode}")
