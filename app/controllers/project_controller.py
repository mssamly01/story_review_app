"""Project file and source chapter controller."""

from __future__ import annotations

from pathlib import Path

from app.domain.project import Project
from app.domain.source_chapter import SourceChapter
from app.services.project_service import ProjectService
from app.services.source_import_service import SourceImportService


class ProjectController:
    def __init__(
        self,
        project_service: ProjectService | None = None,
        source_import_service: SourceImportService | None = None,
    ) -> None:
        self.project_service = project_service or ProjectService()
        self.source_import_service = source_import_service or SourceImportService(
            self.project_service
        )
        self.project: Project | None = None
        self.project_path: Path | None = None

    def create_project(
        self,
        title: str,
        *,
        output_path: str | Path | None = None,
        genre: str = "",
        language: str = "vi",
        default_narration_style: str = "mysterious",
        default_art_style: str = "dark fantasy webtoon",
    ) -> Project:
        self.project = self.project_service.create_project(
            title,
            genre=genre,
            language=language,
            default_narration_style=default_narration_style,
            default_art_style=default_art_style,
        )
        self.project_path = Path(output_path) if output_path is not None else None
        if self.project_path is not None:
            self.save_project(self.project_path)
        return self.project

    def open_project(self, path: str | Path) -> Project:
        self.project_path = Path(path)
        self.project = self.project_service.load_project(self.project_path)
        return self.project

    def save_project(self, path: str | Path | None = None) -> Path:
        project = self.require_project()
        if path is not None:
            self.project_path = Path(path)
        if self.project_path is None:
            raise ValueError("Project path is required before saving.")
        self.project_service.save_project(project, self.project_path)
        return self.project_path

    def add_chapter_from_file(
        self,
        *,
        title: str,
        chapter_number: int,
        text_file: str | Path,
    ) -> SourceChapter:
        project = self.require_project()
        raw_text = Path(text_file).read_text(encoding="utf-8")
        chapter = self.source_import_service.import_raw_text(
            project,
            title=title,
            chapter_number=chapter_number,
            raw_text=raw_text,
        )
        return chapter

    def add_chapter(
        self,
        *,
        title: str,
        chapter_number: int,
        raw_text: str = "",
        notes: str = "",
    ) -> SourceChapter:
        project = self.require_project()
        return self.project_service.add_source_chapter(
            project,
            title=title,
            chapter_number=chapter_number,
            raw_text=raw_text,
            notes=notes,
        )

    def update_chapter(
        self,
        chapter_id: str,
        *,
        title: str | None = None,
        chapter_number: int | None = None,
        raw_text: str | None = None,
    ) -> SourceChapter:
        chapter = self.find_chapter(chapter_id)
        if title is not None:
            chapter.title = title
        if chapter_number is not None:
            chapter.chapter_number = chapter_number
        if raw_text is not None:
            chapter.raw_text = raw_text
        self.require_project().touch()
        return chapter

    def find_chapter(self, chapter_id: str) -> SourceChapter:
        project = self.require_project()
        for chapter in project.source_chapters:
            if chapter.chapter_id == chapter_id:
                return chapter
        raise LookupError(f"SourceChapter not found: {chapter_id}")

    def delete_chapter(self, chapter_id: str) -> None:
        project = self.require_project()
        original_count = len(project.source_chapters)
        project.source_chapters = [
            chapter
            for chapter in project.source_chapters
            if chapter.chapter_id != chapter_id
        ]
        if len(project.source_chapters) == original_count:
            raise LookupError(f"SourceChapter not found: {chapter_id}")
        project.touch()

    def require_project(self) -> Project:
        if self.project is None:
            raise ValueError("No project is open.")
        return self.project
