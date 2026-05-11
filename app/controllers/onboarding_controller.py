"""Thin controller for template-based onboarding."""

from __future__ import annotations

from pathlib import Path

from app.domain.project import Project
from app.domain.project_template import ProjectTemplate
from app.services.project_service import ProjectService
from app.services.project_template_service import ProjectTemplateService


class OnboardingController:
    def __init__(
        self,
        project_service: ProjectService | None = None,
        template_service: ProjectTemplateService | None = None,
    ) -> None:
        self.project_service = project_service or ProjectService()
        self.template_service = template_service or ProjectTemplateService(self.project_service)

    def list_templates(self) -> list[ProjectTemplate]:
        return self.template_service.list_templates()

    def create_project(
        self,
        template_id: str,
        title: str,
        output_path: str | Path,
        project_id: str | None = None,
        language: str | None = None,
    ) -> Project:
        project = self.template_service.create_project_from_template(
            template_id,
            title,
            project_id=project_id,
            language=language,
        )
        self.project_service.save_project(project, output_path)
        return project

    def apply_template(
        self,
        project: Project,
        template_id: str,
        overwrite_existing_styles: bool = False,
    ) -> Project:
        return self.template_service.apply_template_to_project(
            project,
            template_id,
            overwrite_existing_styles=overwrite_existing_styles,
        )
