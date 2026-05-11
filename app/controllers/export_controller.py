"""Export controller for writing episode outputs."""

from __future__ import annotations

from pathlib import Path

from app.domain.project import Project
from app.services.export_service import ExportService
from app.services.project_service import ProjectService


class ExportController:
    def __init__(
        self,
        project_service: ProjectService | None = None,
        export_service: ExportService | None = None,
    ) -> None:
        self.project_service = project_service or ProjectService()
        self.export_service = export_service or ExportService(self.project_service)

    def export_episode(
        self,
        project: Project,
        episode_id: str,
        *,
        export_format: str,
        output_path: str | Path,
    ) -> Path:
        if export_format == "markdown":
            content = self.export_service.export_episode_markdown(project, episode_id)
            return self.export_service.write_text_file(content, output_path)
        if export_format == "json":
            data = self.export_service.export_episode_json(project, episode_id)
            return self.export_service.write_json_file(data, output_path)
        if export_format == "csv":
            content = self.export_service.export_episode_csv(project, episode_id)
            return self.export_service.write_text_file(content, output_path)
        if export_format == "review-txt":
            content = self.export_service.export_review_script_txt(project, episode_id)
            return self.export_service.write_text_file(content, output_path)
        if export_format == "prompts-txt":
            content = self.export_service.export_image_prompts_txt(project, episode_id)
            return self.export_service.write_text_file(content, output_path)
        raise ValueError(f"Unsupported export format: {export_format}")
