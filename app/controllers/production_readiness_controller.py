"""Controller for production readiness workflows."""

from __future__ import annotations

from app.domain.project import Project
from app.services.production_readiness_service import ProductionReadinessService
from app.services.project_service import ProjectService


class ProductionReadinessController:
    def __init__(
        self,
        project_service: ProjectService | None = None,
        readiness_service: ProductionReadinessService | None = None,
    ) -> None:
        self.project_service = project_service or ProjectService()
        self.readiness_service = readiness_service or ProductionReadinessService(
            self.project_service
        )

    def build_episode_report(self, project: Project, episode_id: str):
        return self.readiness_service.build_episode_report(project, episode_id)

    def build_batch_report(self, project: Project, episode_ids: list[str]) -> dict:
        return self.readiness_service.build_batch_report(project, episode_ids)

    def export_episode_report_markdown(
        self,
        project: Project,
        episode_id: str,
    ) -> str:
        return self.readiness_service.export_episode_report_markdown(
            project,
            episode_id,
        )

    def export_batch_report_markdown(
        self,
        project: Project,
        episode_ids: list[str],
    ) -> str:
        return self.readiness_service.export_batch_report_markdown(
            project,
            episode_ids,
        )

    def export_episode_report_json(self, project: Project, episode_id: str) -> dict:
        return self.readiness_service.export_episode_report_json(project, episode_id)
