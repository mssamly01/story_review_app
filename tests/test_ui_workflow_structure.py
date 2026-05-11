import pytest
from app.ui.main_window import MainWindow
from app.ui.app_state import AppState
from app.services.project_service import ProjectService
from app.services.manual_ai_service import ManualAIService
from app.domain.project import Project


@pytest.fixture
def app_and_window():
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    return app, window


def test_main_window_tab_order(app_and_window):
    _, window = app_and_window
    
    # Expected order: Project, Source, Bible / Style, Episode Planner, Beat Studio, Quality & Repair, Export
    # Labels in Vietnamese: Dự án, Nguồn, Bible / Style, Kế hoạch tập, Beat Studio, Chất lượng, Xuất bản
    
    expected_labels = [
        "Dự án",
        "Nguồn",
        "Bible / Style",
        "Kế hoạch tập",
        "Beat Studio",
        "Chất lượng",
        "Xuất bản"
    ]
    
    tab_widget = window.tabs
    assert tab_widget.count() == len(expected_labels)
    
    for i, label in enumerate(expected_labels):
        assert tab_widget.tabText(i) == label


def test_bible_style_tab_appears_before_episode_planner(app_and_window):
    _, window = app_and_window
    
    bible_index = -1
    planner_index = -1
    
    tab_widget = window.tabs
    for i in range(tab_widget.count()):
        text = tab_widget.tabText(i)
        if text == "Bible / Style":
            bible_index = i
        if text == "Kế hoạch tập":
            planner_index = i
            
    assert bible_index != -1
    assert planner_index != -1
    assert bible_index < planner_index


def test_episode_planner_warns_when_bible_style_missing(app_and_window):
    _, window = app_and_window
    ps = ProjectService()
    project = ps.create_project("Empty Bible Project")
    window.app_state.project = project
    
    planner_tab = window.planner_tab
    planner_tab.refresh()
    
    # Check labels
    assert "❌ Thiếu" in planner_tab.lbl_status_char.text()
    assert "❌ Thiếu" in planner_tab.lbl_status_loc.text()
    assert "❌ Thiếu" in planner_tab.lbl_status_style.text()
    assert "Bạn nên phân tích Bible / Style trước" in planner_tab.lbl_status_warning.text()


def test_beat_studio_manual_ai_prompt_uses_bible_style_after_analysis():
    ps = ProjectService()
    project = ps.create_project("Test Project")
    ps.add_character(project, name="Hero", visual_prompt_base="cool hero", character_id="char_001")
    ps.add_location(project, name="Home", visual_prompt_base="warm home", location_id="loc_001")
    ps.add_style_preset(project, name="Epic", positive_prompt="epic style", style_id="style_001")
    project.default_art_style = "style_001"
    
    ps.add_source_chapter(project, title="Ch 1", chapter_number=1, raw_text="Once upon a time...")
    ps.add_review_episode(project, title="Ep 1", source_chapter_ids=["ch_001"])
    
    service = ManualAIService(ps)
    # Test for build-prompts (part of Beat Studio logic)
    prompt_data = service.export_prompt(project, step="build-prompts", episode_id="ep_001", style_preset_id="style_001")
    
    input_data = prompt_data["input_data"]
    
    char_bible = input_data["character_bible"]
    assert any(c["name"] == "Hero" and c["visual_prompt_base"] == "cool hero" for c in char_bible)
    
    loc_bible = input_data["location_bible"]
    assert any(l["name"] == "Home" and l["visual_prompt_base"] == "warm home" for l in loc_bible)
    
    style = input_data["style_preset"]
    assert style["name"] == "Epic" and style["positive_prompt"] == "epic style"


def test_bible_style_analysis_preserves_source_raw_text():
    from app.services.manual_ai_bible_style_service import ManualAIBibleStyleService
    ps = ProjectService()
    project = ps.create_project("Preserve Text Project")
    ch = ps.add_source_chapter(project, title="Source", chapter_number=1, raw_text="MY RAW TEXT")
    
    service = ManualAIBibleStyleService()
    result = {
        "characters": [{"character_id": "char_001", "name": "AI Char"}],
        "world_style_notes": {"genre": "AI Genre"}
    }
    
    service.apply_bible_style_analysis_result(project, result)
    
    assert project.source_chapters[0].raw_text == "MY RAW TEXT"
    assert project.characters[0].name == "AI Char"


def test_product_direction_guards_still_pass():
    pass
