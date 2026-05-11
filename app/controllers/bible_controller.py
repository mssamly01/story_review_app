"""Thin controller for bible management workflows."""

from __future__ import annotations

from app.domain.character import Character
from app.domain.location import Location
from app.domain.project import Project
from app.domain.style_preset import StylePreset
from app.services.bible_service import BibleService


class BibleController:
    def __init__(self, bible_service: BibleService | None = None) -> None:
        self.bible_service = bible_service or BibleService()

    def add_or_update_character(
        self,
        project: Project,
        character: Character,
    ) -> Character:
        return self.bible_service.add_or_update_character(project, character)

    def add_or_update_location(
        self,
        project: Project,
        location: Location,
    ) -> Location:
        return self.bible_service.add_or_update_location(project, location)

    def add_or_update_style_preset(
        self,
        project: Project,
        style: StylePreset,
    ) -> StylePreset:
        return self.bible_service.add_or_update_style_preset(project, style)

    def create_default_style_presets(self, project: Project) -> list[StylePreset]:
        return self.bible_service.create_default_style_presets(project)
