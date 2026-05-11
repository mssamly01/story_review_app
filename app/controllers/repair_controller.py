"""Controller for assisted repair workflows."""

from __future__ import annotations

from app.domain.project import Project
from app.domain.repair import RepairAction
from app.services.project_service import ProjectService
from app.services.quality.repair import RepairSuggestionService


class RepairController:
    def __init__(
        self,
        project_service: ProjectService | None = None,
        repair_service: RepairSuggestionService | None = None,
    ) -> None:
        self.project_service = project_service or ProjectService()
        self.repair_service = repair_service or RepairSuggestionService(self.project_service)

    def suggest_repairs_for_episode(
        self,
        project: Project,
        episode_id: str,
    ) -> list[RepairAction]:
        return self.repair_service.suggest_repairs_for_episode(project, episode_id)

    def suggest_repairs_for_project(self, project: Project) -> list[RepairAction]:
        return self.repair_service.suggest_repairs_for_project(project)

    def apply_repair_action(
        self,
        project: Project,
        action_id: str,
        actions: list[RepairAction],
        allow_medium_risk: bool = False,
        allow_high_risk: bool = False,
    ):
        return self.repair_service.apply_repair_action(
            project,
            action_id,
            actions,
            allow_medium_risk=allow_medium_risk,
            allow_high_risk=allow_high_risk,
        )

    def apply_low_risk_repairs(
        self,
        project: Project,
        actions: list[RepairAction],
    ):
        return self.repair_service.apply_low_risk_repairs(project, actions)
