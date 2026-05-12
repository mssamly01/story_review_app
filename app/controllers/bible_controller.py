"""Thin controller for bible management workflows."""

from __future__ import annotations

from app.domain.character import Character
from app.domain.location import Location
from app.domain.project import Project
from app.domain.style_preset import StylePreset
from app.services.bible_service import BibleService


from app.services.character_reference_prompt_service import CharacterReferencePromptService


from app.services.manual_ai_bible_style_service import ManualAIBibleStyleService


class BibleController:
    def __init__(self, bible_service: BibleService | None = None) -> None:
        self.bible_service = bible_service or BibleService()
        self.char_ref_service = CharacterReferencePromptService()
        self.bible_style_service = ManualAIBibleStyleService()

    def build_bible_style_analysis_prompt(
        self,
        project: Project,
        source_chapter_ids: list[str],
        style_hint: str | None = None
    ) -> str:
        return self.bible_style_service.build_bible_style_analysis_prompt(
            project, source_chapter_ids, style_hint
        )

    def apply_bible_style_analysis_result(
        self,
        project: Project,
        result_json: str | dict,
        overwrite: bool = False
    ) -> dict:
        return self.bible_style_service.apply_bible_style_analysis_result(
            project, result_json, overwrite
        )

    def build_character_reference_prompt(
        self,
        project: Project,
        character_id: str,
        style_preset_id: str | None = None,
        variant_id: str | None = None
    ) -> str:
        return self.char_ref_service.build_reference_sheet_prompt(
            project, character_id, style_preset_id, variant_id=variant_id
        )

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
