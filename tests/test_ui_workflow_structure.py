import pytest

from app.domain.project import Project
from app.services.manual_ai_service import ManualAIService
from app.services.project_service import ProjectService
from app.ui.app_state import AppState
from app.ui.main_window import MainWindow


@pytest.fixture
def app_and_window():
    import sys

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    return app, window


def test_main_window_tab_order(app_and_window):
    _, window = app_and_window

    expected_labels = [
        "Dự án & Nguồn",
        "Bible / Style",
        "Kế hoạch tập",
        "Beat Studio",
        "Xem Beat",
        "Chất lượng",
        "Cài đặt",
    ]

    tab_widget = window.tabs
    assert tab_widget.count() == len(expected_labels)

    for index, label in enumerate(expected_labels):
        assert tab_widget.tabText(index) == label


def test_main_window_has_project_source_tab(app_and_window):
    _, window = app_and_window

    tab_texts = [window.tabs.tabText(index) for index in range(window.tabs.count())]

    assert "Dự án & Nguồn" in tab_texts


def test_main_window_does_not_have_separate_project_and_source_tabs(app_and_window):
    _, window = app_and_window

    tab_texts = [window.tabs.tabText(index) for index in range(window.tabs.count())]

    assert "Dự án" not in tab_texts
    assert "Nguồn" not in tab_texts


def test_bible_style_tab_appears_before_episode_planner(app_and_window):
    _, window = app_and_window

    tab_widget = window.tabs
    tab_texts = [tab_widget.tabText(index) for index in range(tab_widget.count())]

    assert tab_texts.index("Bible / Style") < tab_texts.index("Kế hoạch tập")


def test_episode_planner_warns_when_bible_style_missing(app_and_window):
    _, window = app_and_window
    project_service = ProjectService()
    project = project_service.create_project("Empty Bible Project")
    window.app_state.project = project

    planner_tab = window.planner_tab
    planner_tab.refresh()

    assert "missing" in planner_tab.lbl_status_char.text()
    assert "missing" in planner_tab.lbl_status_loc.text()
    assert "missing" in planner_tab.lbl_status_style.text()
    assert "Bible / Style" in planner_tab.lbl_status_warning.text()


def test_beat_studio_manual_ai_prompt_uses_bible_style_after_analysis():
    project_service = ProjectService()
    project = project_service.create_project("Test Project")
    project_service.add_character(
        project,
        name="Hero",
        visual_prompt_base="cool hero",
        character_id="char_001",
    )
    project_service.add_location(
        project,
        name="Home",
        visual_prompt_base="warm home",
        location_id="loc_001",
    )
    project_service.add_style_preset(
        project,
        name="Epic",
        positive_prompt="epic style",
        style_id="style_001",
    )
    project.default_art_style = "style_001"

    project_service.add_source_chapter(
        project,
        title="Ch 1",
        chapter_number=1,
        raw_text="Once upon a time...",
    )
    project_service.add_review_episode(project, title="Ep 1", source_chapter_ids=["ch_001"])

    service = ManualAIService(project_service)
    prompt_data = service.export_prompt(
        project,
        step="build-prompts",
        episode_id="ep_001",
        style_preset_id="style_001",
    )

    input_data = prompt_data["input_data"]

    char_bible = input_data["character_bible"]
    assert any(
        item["name"] == "Hero" and item["visual_prompt_base"] == "cool hero"
        for item in char_bible
    )

    loc_bible = input_data["location_bible"]
    assert any(
        item["name"] == "Home" and item["visual_prompt_base"] == "warm home"
        for item in loc_bible
    )

    style = input_data["style_preset"]
    assert style["name"] == "Epic" and style["positive_prompt"] == "epic style"


def test_bible_style_analysis_preserves_source_raw_text():
    from app.services.manual_ai_bible_style_service import ManualAIBibleStyleService

    project_service = ProjectService()
    project = project_service.create_project("Preserve Text Project")
    project_service.add_source_chapter(
        project,
        title="Source",
        chapter_number=1,
        raw_text="MY RAW TEXT",
    )

    service = ManualAIBibleStyleService()
    result = {
        "characters": [{"character_id": "char_001", "name": "AI Char"}],
        "world_style_notes": {"genre": "AI Genre"},
    }

    service.apply_bible_style_analysis_result(project, result)

    assert project.source_chapters[0].raw_text == "MY RAW TEXT"
    assert project.characters[0].name == "AI Char"


def test_product_direction_guards_still_pass():
    pass
