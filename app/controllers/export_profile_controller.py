"""Controller for export profile workflows."""

from __future__ import annotations

from pathlib import Path

from app.domain.export_profile import ExportProfile
from app.domain.project import Project
from app.services.export_profile_service import ExportProfileService
from app.services.project_service import ProjectService


class ExportProfileController:
    def __init__(
        self,
        project_service: ProjectService | None = None,
        export_profile_service: ExportProfileService | None = None,
    ) -> None:
        self.project_service = project_service or ProjectService()
        self.export_profile_service = (
            export_profile_service or ExportProfileService(self.project_service)
        )

    def list_profiles(self) -> list[ExportProfile]:
        return self.export_profile_service.list_profiles()

    def get_profile(self, profile_id: str) -> ExportProfile:
        return self.export_profile_service.get_profile(profile_id)

    def export_episode_with_profile(
        self,
        project: Project,
        episode_id: str,
        profile_id: str,
        output_dir: str | Path,
    ) -> list[Path]:
        return self.export_profile_service.export_episode_with_profile(
            project,
            episode_id,
            profile_id,
            output_dir,
        )

    def export_batch_with_profile(
        self,
        project: Project,
        episode_ids: list[str],
        profile_id: str,
        output_dir: str | Path,
    ) -> list[Path]:
        return self.export_profile_service.export_batch_with_profile(
            project,
            episode_ids,
            profile_id,
            output_dir,
        )
