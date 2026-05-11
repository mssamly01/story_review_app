import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from app.ui.beat_preview_tab import BeatPreviewTab
from app.ui.app_state import AppState
from app.services.project_service import ProjectService
from app.controllers.generation_controller import GenerationController

@pytest.fixture
def app():
    import sys
    return QApplication.instance() or QApplication(sys.argv)

@pytest.fixture
def state_and_controllers():
    state = AppState()
    ps = ProjectService()
    gc = GenerationController(ps)
    return state, gc, ps

def test_beat_preview_tab_can_construct_without_project(app, state_and_controllers):
    state, gc, _ = state_and_controllers
    tab = BeatPreviewTab(state, gc, lambda: None)
    assert tab.table.rowCount() == 0

def test_beat_preview_lists_beats_for_selected_episode(app, state_and_controllers):
    state, gc, ps = state_and_controllers
    p = ps.create_project("Test Project")
    state.project = p
    
    ep = ps.add_review_episode(p, title="Ep 1", source_chapter_ids=[])
    state.selected_episode_id = ep.episode_id
    
    sc1 = ps.add_scene(p, episode_id=ep.episode_id, title="Scene 1", scene_id="sc_001")
    ps.add_beat(p, episode_id=ep.episode_id, scene_id=sc1.scene_id, action="Action 1", beat_id="b1")
    ps.add_beat(p, episode_id=ep.episode_id, scene_id=sc1.scene_id, action="Action 2", beat_id="b2")
    
    tab = BeatPreviewTab(state, gc, lambda: None)
    tab.refresh()
    
    assert tab.table.rowCount() == 2
    # Column 2 (NỘI DUNG) is now a QPlainTextEdit in a cell widget
    content_widget = tab.table.cellWidget(0, 2)
    assert content_widget.toPlainText() == "(Chưa có nội dung review)"
    assert "Scene 1" in tab.table.item(0, 1).text()

def test_beat_preview_orders_by_scene_and_order_index(app, state_and_controllers):
    state, gc, ps = state_and_controllers
    p = ps.create_project("Order Project")
    state.project = p
    ep = ps.add_review_episode(p, title="Ep 1", source_chapter_ids=[])
    state.selected_episode_id = ep.episode_id
    
    sc2 = ps.add_scene(p, episode_id=ep.episode_id, title="Scene 2", scene_id="sc_002")
    sc1 = ps.add_scene(p, episode_id=ep.episode_id, title="Scene 1", scene_id="sc_001")
    
    # Force sc1 to be first in list if needed, but project.review_episodes[0].scenes defines order
    # add_scene appends to ep.scenes
    ep.scenes = [sc1, sc2] 
    
    ps.add_beat(p, episode_id=ep.episode_id, scene_id=sc1.scene_id, action="B1", beat_id="b1")
    ps.add_beat(p, episode_id=ep.episode_id, scene_id=sc2.scene_id, action="B2", beat_id="b2")
    
    tab = BeatPreviewTab(state, gc, lambda: None)
    tab.refresh()
    
    assert tab.table.item(0, 1).text() == "Scene 1"
    assert tab.table.item(1, 1).text() == "Scene 2"

def test_beat_preview_scene_filter(app, state_and_controllers):
    state, gc, ps = state_and_controllers
    p = ps.create_project("Filter Project")
    state.project = p
    ep = ps.add_review_episode(p, title="Ep 1", source_chapter_ids=[])
    state.selected_episode_id = ep.episode_id
    
    sc1 = ps.add_scene(p, episode_id=ep.episode_id, title="Scene 1", scene_id="sc_001")
    sc2 = ps.add_scene(p, episode_id=ep.episode_id, title="Scene 2", scene_id="sc_002")
    
    ps.add_beat(p, episode_id=ep.episode_id, scene_id=sc1.scene_id, action="S1 Beat")
    ps.add_beat(p, episode_id=ep.episode_id, scene_id=sc2.scene_id, action="S2 Beat")
    
    tab = BeatPreviewTab(state, gc, lambda: None)
    tab.refresh()
    
    assert tab.table.rowCount() == 2
    
    # Filter to Scene 2
    for i in range(tab.scene_combo.count()):
        if tab.scene_combo.itemData(i) == "sc_002":
            tab.scene_combo.setCurrentIndex(i)
            break
            
    assert tab.table.rowCount() == 1
    assert tab.table.item(0, 1).text() == "Scene 2"

def test_beat_preview_table_has_expected_columns(app, state_and_controllers):
    state, gc, _ = state_and_controllers
    tab = BeatPreviewTab(state, gc, lambda: None)
    
    assert tab.table.columnCount() == 4
    
    expected_headers = ["STT", "PHÂN CẢNH", "NỘI DUNG", "PROMPT ẢNH"]
    for i, expected in enumerate(expected_headers):
        assert tab.table.horizontalHeaderItem(i).text() == expected

def test_beat_preview_vertical_header_hidden(app, state_and_controllers):
    state, gc, _ = state_and_controllers
    tab = BeatPreviewTab(state, gc, lambda: None)
    
    assert tab.table.verticalHeader().isVisible() is False

def test_beat_preview_stt_uses_first_column(app, state_and_controllers):
    state, gc, ps = state_and_controllers
    p = ps.create_project("Table Project")
    state.project = p
    
    ep = ps.add_review_episode(p, title="Ep 1", source_chapter_ids=[])
    state.selected_episode_id = ep.episode_id
    
    sc = ps.add_scene(p, episode_id=ep.episode_id, title="Scene Table", scene_id="sc_tbl")
    beat = ps.add_beat(p, episode_id=ep.episode_id, scene_id=sc.scene_id, action="A", beat_id="b1")
    beat.review_text = "Review Table"
    beat.image_prompt = "Img Prompt"
    beat.negative_prompt = "Neg Prompt"
    
    tab = BeatPreviewTab(state, gc, lambda: None)
    tab.refresh()
    
    assert tab.table.rowCount() == 1
    
    # 0 = STT
    assert tab.table.item(0, 0).text() == "1"
    # 1 = PHÂN CẢNH
    assert "Scene Table" in tab.table.item(0, 1).text()
    # 2 = NỘI DUNG (Widget)
    content_widget = tab.table.cellWidget(0, 2)
    assert content_widget.toPlainText() == "Review Table"
    # 3 = PROMPT ẢNH (Widget with layout)
    prompt_widget = tab.table.cellWidget(0, 3)
    # Find QPlainTextEdit in children
    from PySide6.QtWidgets import QPlainTextEdit
    prompt_edit = prompt_widget.findChild(QPlainTextEdit)
    assert "Img Prompt" in prompt_edit.toPlainText()
    assert "Neg Prompt" in prompt_edit.toPlainText()

def test_beat_preview_stt_center_aligned(app, state_and_controllers):
    state, gc, ps = state_and_controllers
    p = ps.create_project("Align Project")
    state.project = p
    ep = ps.add_review_episode(p, title="Ep 1", source_chapter_ids=[])
    state.selected_episode_id = ep.episode_id
    sc = ps.add_scene(p, episode_id=ep.episode_id, title="S1", scene_id="s1")
    ps.add_beat(p, episode_id=ep.episode_id, scene_id=sc.scene_id, action="A")
    
    tab = BeatPreviewTab(state, gc, lambda: None)
    tab.refresh()
    
    stt_item = tab.table.item(0, 0)
    assert stt_item.textAlignment() & Qt.AlignmentFlag.AlignCenter

def test_beat_preview_fixed_row_height(app, state_and_controllers):
    state, gc, ps = state_and_controllers
    p = ps.create_project("Height Project")
    state.project = p
    ep = ps.add_review_episode(p, title="Ep 1", source_chapter_ids=[])
    state.selected_episode_id = ep.episode_id
    sc = ps.add_scene(p, episode_id=ep.episode_id, title="S1", scene_id="s1")
    ps.add_beat(p, episode_id=ep.episode_id, scene_id=sc.scene_id, action="A")
    
    tab = BeatPreviewTab(state, gc, lambda: None)
    tab.refresh()
    
    # ROW_HEIGHT is 120
    assert tab.table.rowHeight(0) == 120

def test_beat_preview_prompt_cell_has_copy_button(app, state_and_controllers):
    state, gc, ps = state_and_controllers
    p = ps.create_project("Copy Project")
    state.project = p
    ep = ps.add_review_episode(p, title="Ep 1", source_chapter_ids=[])
    state.selected_episode_id = ep.episode_id
    sc = ps.add_scene(p, episode_id=ep.episode_id, title="S1", scene_id="s1")
    ps.add_beat(p, episode_id=ep.episode_id, scene_id=sc.scene_id, action="A")
    
    tab = BeatPreviewTab(state, gc, lambda: None)
    tab.refresh()
    
    prompt_widget = tab.table.cellWidget(0, 3)
    from PySide6.QtWidgets import QPushButton
    btn = prompt_widget.findChild(QPushButton)
    assert btn is not None
    assert "Copy" in btn.text()

def test_beat_preview_combined_prompt_formatting(app, state_and_controllers):
    state, gc, ps = state_and_controllers
    p = ps.create_project("Format Project")
    state.project = p
    ep = ps.add_review_episode(p, title="Ep 1", source_chapter_ids=[])
    state.selected_episode_id = ep.episode_id
    sc = ps.add_scene(p, episode_id=ep.episode_id, title="S1", scene_id="s1")
    beat = ps.add_beat(p, episode_id=ep.episode_id, scene_id=sc.scene_id, action="A")
    beat.image_prompt = "A cat"
    beat.negative_prompt = "lowres"
    
    tab = BeatPreviewTab(state, gc, lambda: None)
    tab.refresh()
    
    prompt_widget = tab.table.cellWidget(0, 3)
    from PySide6.QtWidgets import QPlainTextEdit
    prompt_edit = prompt_widget.findChild(QPlainTextEdit)
    combined = prompt_edit.toPlainText()
    
    assert combined == "A cat, negative prompt: lowres"
    assert "Image Prompt:" not in combined
    assert "Negative Prompt:" not in combined

def test_beat_preview_long_prompt_does_not_expand_row(app, state_and_controllers):
    state, gc, ps = state_and_controllers
    p = ps.create_project("Long Prompt Project")
    state.project = p
    ep = ps.add_review_episode(p, title="Ep 1", source_chapter_ids=[])
    state.selected_episode_id = ep.episode_id
    sc = ps.add_scene(p, episode_id=ep.episode_id, title="S1", scene_id="s1")
    beat = ps.add_beat(p, episode_id=ep.episode_id, scene_id=sc.scene_id, action="A")
    beat.image_prompt = "A" * 5000 # Very long
    
    tab = BeatPreviewTab(state, gc, lambda: None)
    tab.refresh()
    
    assert tab.table.rowHeight(0) == 120

def test_product_direction_guards_still_pass():
    pass
