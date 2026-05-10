"""Source chapter import workflow.

This service stores original story text as SourceChapter data. It does not
parse, summarize, rewrite, or generate AI output.
"""

from __future__ import annotations

from app.domain.project import Project
from app.domain.source_chapter import SourceChapter
from app.services.project_service import ProjectService


class SourceImportService:
    def __init__(self, project_service: ProjectService | None = None) -> None:
        self.project_service = project_service or ProjectService()

    def import_raw_text(
        self,
        project: Project,
        *,
        title: str,
        chapter_number: int,
        raw_text: str,
        notes: str = "",
        chapter_id: str | None = None,
    ) -> SourceChapter:
        self._validate_import(title=title, chapter_number=chapter_number)
        return self.project_service.add_source_chapter(
            project,
            title=title,
            chapter_number=chapter_number,
            raw_text=raw_text,
            notes=notes,
            chapter_id=chapter_id,
        )

    def _validate_import(self, *, title: str, chapter_number: int) -> None:
        if not title.strip():
            raise ValueError("SourceChapter title is required.")
        if chapter_number < 1:
            raise ValueError("SourceChapter chapter_number must be at least 1.")
