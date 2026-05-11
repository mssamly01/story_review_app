"""Validation controller for CLI and UI entry points."""

from __future__ import annotations

from app.domain.project import Project
from app.domain.validation import ValidationIssue
from app.services.continuity_checker_service import ContinuityCheckerService
from app.services.project_service import ProjectService
from app.services.quality.validation import ProjectValidationService


class ValidationController:
    def __init__(
        self,
        project_service: ProjectService | None = None,
        project_validation_service: ProjectValidationService | None = None,
        continuity_checker_service: ContinuityCheckerService | None = None,
    ) -> None:
        self.project_service = project_service or ProjectService()
        self.project_validation_service = (
            project_validation_service or ProjectValidationService()
        )
        self.continuity_checker_service = (
            continuity_checker_service
            or ContinuityCheckerService(self.project_service)
        )

    def validate_project(
        self, project: Project, episode_id: str | None = None
    ) -> list[ValidationIssue]:
        if episode_id:
            issues = self.project_validation_service.validate_episode(
                project,
                episode_id,
            )
            try:
                issues.extend(
                    self.continuity_checker_service.check_episode(
                        project,
                        episode_id,
                    )
                )
            except LookupError as exc:
                issues.append(
                    ValidationIssue(
                        issue_id=f"val_{len(issues) + 1:03d}",
                        severity="error",
                        category="broken_reference",
                        message=str(exc),
                        suggestion="Choose an existing review episode.",
                        entity_type="ReviewEpisode",
                        entity_id=episode_id,
                        episode_id=episode_id,
                    )
                )
            return issues

        issues = self.project_validation_service.validate_project(project)
        for episode in project.review_episodes:
            issues.extend(
                self.continuity_checker_service.check_episode(
                    project,
                    episode.episode_id,
                )
            )
        return issues

    def has_errors(self, issues: list[ValidationIssue]) -> bool:
        return any(issue.severity == "error" for issue in issues)
