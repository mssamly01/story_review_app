from __future__ import annotations

import os
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.controllers.project_controller import ProjectController
from app.services.project_service import ProjectService
from app.ui.app_state import AppState
from app.ui.project_source_tab import ProjectSourceTab


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _build_tab() -> tuple[ProjectSourceTab, AppState, ProjectController]:
    _app()
    state = AppState()
    controller = ProjectController()
    tab = ProjectSourceTab(state, controller, MagicMock())
    return tab, state, controller


def test_project_source_tab_can_construct_without_project():
    tab, state, _controller = _build_tab()

    tab.refresh()

    assert state.project is None
    assert tab.chapter_list.count() == 0


def test_project_source_tab_displays_project_fields():
    tab, state, controller = _build_tab()
    project = controller.create_project(
        "Demo Story",
        genre="dark fantasy",
        language="vi",
        default_narration_style="mysterious",
        default_art_style="dark fantasy webtoon",
    )
    state.project = project

    tab.refresh()

    assert tab.title_edit.text() == "Demo Story"
    assert tab.genre_edit.text() == "dark fantasy"
    assert tab.language_combo.currentText() == "vi"


def test_project_source_tab_lists_chapters():
    tab, state, controller = _build_tab()
    project = controller.create_project("Demo Story")
    controller.add_chapter(title="Chapter 1", chapter_number=1, raw_text="One")
    controller.add_chapter(title="Chapter 2", chapter_number=2, raw_text="Two")
    state.project = project

    tab.refresh()

    assert tab.chapter_list.count() == 2
    assert "Chapter 1" in tab.chapter_list.item(0).text()
    assert "Chapter 2" in tab.chapter_list.item(1).text()


def test_project_source_tab_selecting_chapter_updates_app_state():
    tab, state, controller = _build_tab()
    project = controller.create_project("Demo Story")
    ch1 = controller.add_chapter(title="Chapter 1", chapter_number=1, raw_text="One")
    ch2 = controller.add_chapter(title="Chapter 2", chapter_number=2, raw_text="Two")
    state.project = project
    state.selected_chapter_id = ch1.chapter_id
    tab.refresh()

    tab.chapter_list.setCurrentRow(1)

    assert state.selected_chapter_id == ch2.chapter_id
    assert tab.raw_text_edit.toPlainText() == "Two"


def test_project_source_tab_saving_chapter_preserves_raw_text():
    tab, state, controller = _build_tab()
    project = controller.create_project("Demo Story")
    chapter = controller.add_chapter(
        title="Chapter 1",
        chapter_number=1,
        raw_text="Original source text",
    )
    state.project = project
    state.selected_chapter_id = chapter.chapter_id
    tab.refresh()

    tab.raw_text_edit.setPlainText("Intentional edited source text")
    tab._on_save_chapter()

    assert project.source_chapters[0].raw_text == "Intentional edited source text"


def test_generation_services_still_do_not_modify_source_raw_text():
    project_service = ProjectService()
    project = project_service.create_project("Demo Story")
    chapter = project_service.add_source_chapter(
        project,
        title="Chapter 1",
        chapter_number=1,
        raw_text="KEEP THIS SOURCE EXACTLY",
    )
    before = chapter.raw_text

    from app.services.episode_planner_service import EpisodePlannerService
    from app.services.beat_generator_service import BeatGeneratorService
    from app.services.review_rewriter_service import ReviewRewriterService
    from app.services.prompt_builder_service import PromptBuilderService

    episode = EpisodePlannerService(project_service).plan_episode(
        project,
        selected_source_chapter_ids=[chapter.chapter_id],
        narration_style="mysterious",
        retelling_density="balanced",
        episode_title="Episode 1",
    )
    BeatGeneratorService(project_service).generate_beats_for_episode(
        project,
        episode.episode_id,
        retelling_density="balanced",
    )
    ReviewRewriterService().rewrite_episode(project, episode.episode_id)
    PromptBuilderService().build_prompts_for_episode(project, episode.episode_id)

    assert chapter.raw_text == before
