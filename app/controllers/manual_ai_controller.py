"""Controller for Manual AI workflow (export prompt → external AI → import result)."""

from __future__ import annotations

from typing import Any

from app.domain.project import Project
from app.services.manual_ai_service import ManualAIService
from app.services.project_service import ProjectService


class ManualAIController:
    """UI calls this controller; controller delegates to ManualAIService."""

    def __init__(self, project_service: ProjectService | None = None) -> None:
        self.project_service = project_service or ProjectService()
        self.service = ManualAIService(self.project_service)

    def export_prompt(
        self,
        project: Project,
        step: str,
        *,
        chapter_id: str | None = None,
        chapter_ids: list[str] | None = None,
        episode_id: str | None = None,
        episode_title: str | None = None,
        tone: str | None = None,
        density: str | None = None,
        style_preset_id: str | None = None,
    ) -> str:
        """Return clipboard-ready prompt text."""
        exported = self.service.export_prompt(
            project,
            step=step,
            chapter_id=chapter_id,
            chapter_ids=chapter_ids,
            episode_id=episode_id,
            episode_title=episode_title,
            tone=tone,
            density=density,
            style_preset_id=style_preset_id,
        )
        return self.service.format_prompt_for_clipboard(exported)

    def import_result(
        self,
        project: Project,
        step: str,
        result_data: dict[str, Any],
        *,
        chapter_id: str | None = None,
        chapter_ids: list[str] | None = None,
        episode_id: str | None = None,
        tone: str | None = None,
        density: str | None = None,
        style_preset_id: str | None = None,
    ) -> str:
        """Apply AI result to project. Returns summary message."""
        return self.service.import_result(
            project,
            step=step,
            result_data=result_data,
            chapter_id=chapter_id,
            chapter_ids=chapter_ids,
            episode_id=episode_id,
            tone=tone,
            density=density,
            style_preset_id=style_preset_id,
        )
