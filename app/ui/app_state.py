"""UI state object for the PySide6 application."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.project import Project


@dataclass
class AppState:
    """Lightweight object to store current UI selection and project context."""

    project: Project | None = None
    project_path: Path | None = None
    selected_chapter_id: str | None = None
    selected_episode_id: str | None = None
    selected_scene_id: str | None = None
    selected_beat_id: str | None = None
    ai_mode: str = "deterministic"
    model: str | None = None

    def has_project(self) -> bool:
        return self.project is not None
