"""Controller for prompt quality scoring workflows."""

from __future__ import annotations

from app.domain.project import Project
from app.services.project_service import ProjectService
from app.services.quality.prompt import PromptQualityService


class PromptQualityController:
    def __init__(
        self,
        project_service: ProjectService | None = None,
        prompt_quality_service: PromptQualityService | None = None,
    ) -> None:
        self.project_service = project_service or ProjectService()
        self.prompt_quality_service = prompt_quality_service or PromptQualityService(
            self.project_service
        )

    def score_episode_prompts(self, project: Project, episode_id: str):
        return self.prompt_quality_service.score_episode_prompts(project, episode_id)

    def build_episode_report(self, project: Project, episode_id: str) -> dict:
        return self.prompt_quality_service.build_episode_report(project, episode_id)

    def export_episode_report_markdown(
        self,
        project: Project,
        episode_id: str,
    ) -> str:
        return self.prompt_quality_service.export_episode_report_markdown(
            project,
            episode_id,
        )
