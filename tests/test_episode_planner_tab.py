from __future__ import annotations

import json
import os
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.controllers.batch_workflow_controller import BatchWorkflowController
from app.controllers.generation_controller import GenerationController
from app.controllers.manual_ai_controller import ManualAIController
from app.controllers.project_controller import ProjectController
from app.domain.character import CharacterOutfit, CharacterVariant
from app.services.manual_ai_episode_planner_service import ManualAIEpisodePlannerService
from app.services.project_service import ProjectService
from app.ui.app_state import AppState
from app.ui.beat_studio_tab import BeatStudioTab
from app.ui.episode_planner_tab import EpisodePlannerTab


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _sample_project():
    project_service = ProjectService()
    project = project_service.create_project(
        "Planner UI Story",
        genre="mystery",
        language="vi",
        default_narration_style="mysterious",
        default_art_style="dark_webtoon",
    )
    chapter = project_service.add_source_chapter(
        project,
        title="Chapter One",
        chapter_number=1,
        raw_text="Lâm Vũ trở về căn nhà cũ và phát hiện một lá thư dưới sàn.",
    )
    character = project_service.add_character(
        project,
        character_id="lam_vu",
        name="Lâm Vũ",
        visual_prompt_base="young man with messy black hair",
    )
    character.variants = [
        CharacterVariant(
            variant_id="lam_vu_young",
            character_id="lam_vu",
            display_name="Lam Vu - young",
            state_type="young",
            visual_prompt_base="young boy with messy black hair",
        ),
        CharacterVariant(
            variant_id="lam_vu_old",
            character_id="lam_vu",
            display_name="Lam Vu - old",
            state_type="old",
            visual_prompt_base="old man with white hair",
        ),
    ]
    character.outfits = [
        CharacterOutfit(
            outfit_id="outfit_lam_vu_young_sleepwear",
            character_id="lam_vu",
            variant_id="lam_vu_young",
            display_name="Blue gray inner robe",
            description="simple ancient inner robe",
        ),
        CharacterOutfit(
            outfit_id="outfit_lam_vu_old_battle",
            character_id="lam_vu",
            variant_id="lam_vu_old",
            display_name="Torn battle robe",
            description="torn old battle robe",
        ),
    ]
    project_service.add_location(
        project,
        location_id="old_house",
        name="Old House",
        visual_prompt_base="dusty old house",
    )
    project_service.add_style_preset(
        project,
        style_id="dark_webtoon",
        name="Dark Webtoon",
        positive_prompt="cinematic dark webtoon style",
    )
    return project, project_service, chapter


def _planner_result(chapter_id: str) -> dict:
    return {
        "episode": {
            "episode_id": "ep_ui_001",
            "title": "The Old House",
            "summary": "Lâm Vũ enters the old house.",
            "hook": "The house is not empty.",
            "cliffhanger": "A warning appears.",
            "source_chapter_ids": [chapter_id],
            "narration_style": "mysterious",
            "retelling_density": "full",
        },
        "scenes": [
            {
                "scene_id": "sc_001",
                "title": "Front Door",
                "summary": "He enters the house.",
                "mood": "tense",
                "characters": ["lam_vu"],
                "location": "old_house",
                "target_beats": 2,
                "beats": [
                    {
                        "beat_id": "beat_sc_001_001",
                        "scene_id": "sc_001",
                        "order_index": 1,
                        "story_function": "hook",
                        "characters": ["lam_vu"],
                        "character_variants": {"lam_vu": "lam_vu_young"},
                        "character_outfits": {"lam_vu": "outfit_lam_vu_young_sleepwear"},
                        "location": "old_house",
                        "action": "Lâm Vũ opens the old door.",
                        "emotion": "tense",
                        "camera": "slow push-in",
                        "shot_type": "wide shot",
                        "timeOfDay": "Night",
                        "lighting": "moonlight through broken window",
                        "atmosphere": "dusty silence",
                        "location_cues": "old wooden door, cracked threshold",
                        "asmr_visuals": "floating dust, trembling curtain",
                        "composition": "small figure framed by a tall doorway",
                        "posture": "hand on door, shoulders raised",
                        "expression": "anxious eyes",
                        "body_language": "hesitant forward lean",
                        "visual_description": "He stands before the doorway.",
                        "review_text": "Lâm Vũ chậm rãi mở cánh cửa cũ, và cảm giác bất an lập tức bao trùm lấy anh.",
                        "continuity_tags": ["old house", "door"],
                        "props": ["old key"],
                        "wardrobe_notes": "black jacket damp from rain",
                        "character_state": "tired but alert",
                        "location_state": "abandoned house disturbed",
                        "transition_note": "from rain outside to dark hallway",
                    },
                    {
                        "beat_id": "beat_sc_001_002",
                        "scene_id": "sc_001",
                        "order_index": 2,
                        "story_function": "discovery",
                        "characters": ["lam_vu"],
                        "character_states": [
                            {
                                "character_id": "lam_vu",
                                "variant_id": "lam_vu_old",
                                "outfit_id": "outfit_lam_vu_old_battle",
                            }
                        ],
                        "location": "old_house",
                        "action": "He notices a loose floorboard.",
                        "emotion": "curious",
                        "shot_type": "close-up",
                        "visual_description": "His hand touches the loose board.",
                        "review_text": "Ngay khi cúi xuống, anh nhận ra một tấm ván sàn bị cạy lên như vừa có ai động vào.",
                        "continuity_tags": ["floorboard"],
                    },
                ],
            },
            {
                "scene_id": "sc_002",
                "title": "Hidden Letter",
                "summary": "He finds the letter.",
                "mood": "suspicious",
                "characters": ["lam_vu"],
                "location": "old_house",
                "target_beats": 1,
                "beats": [
                    {
                        "beat_id": "beat_sc_002_001",
                        "scene_id": "sc_002",
                        "order_index": 1,
                        "story_function": "reveal",
                        "characters": ["lam_vu"],
                        "location": "old_house",
                        "action": "He reads the letter.",
                        "emotion": "shocked",
                        "shot_type": "detail shot",
                        "visual_description": "A warning line is visible.",
                        "review_text": "Lá thư khiến anh hiểu rằng có người đã biết trước ngày anh quay về.",
                        "continuity_tags": ["letter"],
                    }
                ],
            },
        ],
    }


def _build_tab(project, project_service, chapter):
    _app()
    app_state = AppState(project=project, selected_chapter_ids=[chapter.chapter_id])
    tab = EpisodePlannerTab(
        app_state,
        ProjectController(project_service),
        GenerationController(project_service),
        BatchWorkflowController(project_service),
        ManualAIController(project_service),
        Mock(),
    )
    tab.refresh()
    return tab, app_state


def test_episode_planner_tab_has_required_sections():
    project, project_service, chapter = _sample_project()
    tab, _ = _build_tab(project, project_service, chapter)

    assert tab.setup_group.title() == "Episode Setup"
    assert tab.prompt_workflow_group.title() == "Manual AI Prompt Workflow"
    assert tab.structure_preview_group.title() == "Episode Structure Preview"
    assert tab.bible_status_group.title() == "Bible / Style readiness"
    assert tab.prompt_preview.isReadOnly()
    assert tab.result_input is not None
    assert tab.scene_tree is not None
    assert tab.scene_tree.columnCount() == 4
    assert not hasattr(tab, "scene_list")
    assert tab.manual_task_combo.currentData() == "plan-episode-with-review"
    assert tab._current_density() == "full"
    assert "80-110 beat" in tab.density_helper_label.text()


def test_episode_planner_density_options_are_long_form_review_targets():
    project, project_service, chapter = _sample_project()
    tab, _ = _build_tab(project, project_service, chapter)

    labels = [tab.density_combo.itemText(index) for index in range(tab.density_combo.count())]

    assert "Ngắn: 30-45 beat" in labels
    assert "Cân bằng: 50-70 beat" in labels
    assert "Đầy đủ: 80-110 beat" in labels
    assert "Siêu chi tiết: 110-150 beat" in labels


def test_episode_planner_preview_lists_scenes_and_beats():
    project, project_service, chapter = _sample_project()
    ManualAIEpisodePlannerService(project_service).apply_episode_plan_with_review_result(
        project,
        _planner_result(chapter.chapter_id),
    )
    tab, app_state = _build_tab(project, project_service, chapter)
    app_state.selected_episode_id = "ep_ui_001"
    tab.refresh()

    assert tab.scene_tree.topLevelItemCount() == 2
    
    scene1 = tab.scene_tree.topLevelItem(0)
    assert "Front Door" in scene1.text(0)
    assert "2 beats" in scene1.text(0)
    assert scene1.childCount() == 2
    assert "Beat 1" in scene1.child(0).text(0)
    assert "Beat 2" in scene1.child(1).text(0)
    
    scene2 = tab.scene_tree.topLevelItem(1)
    assert "Hidden Letter" in scene2.text(0)
    assert "Lâm Vũ" in scene1.child(0).text(0)


def test_episode_planner_detail_save_updates_only_story_fields():
    project, project_service, chapter = _sample_project()
    ManualAIEpisodePlannerService(project_service).apply_episode_plan_with_review_result(
        project,
        _planner_result(chapter.chapter_id),
    )
    tab, app_state = _build_tab(project, project_service, chapter)
    app_state.selected_episode_id = "ep_ui_001"
    tab.refresh()
    
    scene_item = tab.scene_tree.topLevelItem(0)
    beat_item = scene_item.child(0)
    tab.scene_tree.setCurrentItem(beat_item)

    beat = project.review_episodes[0].scenes[0].beats[0]
    beat.image_prompt = "keep image prompt"
    beat.negative_prompt = "keep negative prompt"

    tab.beat_action_edit.setText("Updated action")
    tab.beat_emotion_edit.setText("determined")
    tab.beat_visual_description_edit.setText("Updated visual")
    tab.beat_shot_type_edit.setText("medium shot")
    tab.beat_review_text_edit.setPlainText("Review text đã được chỉnh sửa.")
    tab.beat_continuity_tags_edit.setText("updated, story")
    tab._on_save_beat_text_changes()

    assert beat.action == "Updated action"
    assert beat.emotion == "determined"
    assert beat.visual_description == "Updated visual"
    assert beat.shot_type == "medium shot"
    assert beat.review_text == "Review text đã được chỉnh sửa."
    assert beat.continuity_tags == ["updated", "story"]
    assert beat.image_prompt == "keep image prompt"
    assert beat.negative_prompt == "keep negative prompt"
    assert chapter.raw_text == "Lâm Vũ trở về căn nhà cũ và phát hiện một lá thư dưới sàn."


def test_episode_planner_selected_beat_editor_displays_all_fields():
    project, project_service, chapter = _sample_project()
    ManualAIEpisodePlannerService(project_service).apply_episode_plan_with_review_result(
        project,
        _planner_result(chapter.chapter_id),
    )
    tab, app_state = _build_tab(project, project_service, chapter)
    app_state.selected_episode_id = "ep_ui_001"
    tab.refresh()

    beat_item = tab.scene_tree.topLevelItem(0).child(0)
    tab.scene_tree.setCurrentItem(beat_item)
    tab._on_structure_item_select()

    assert tab.beat_id_edit.text() == "beat_sc_001_001"
    assert tab.beat_scene_id_edit.text() == "sc_001"
    assert tab.beat_order_index_edit.text() == "1"
    assert tab.beat_story_function_edit.text() == "hook"
    assert tab.beat_camera_edit.text() == "slow push-in"
    assert tab.beat_time_of_day_edit.text() == "Night"
    assert tab.beat_lighting_edit.text() == "moonlight through broken window"
    assert tab.beat_atmosphere_edit.text() == "dusty silence"
    assert tab.beat_location_cues_edit.text() == "old wooden door, cracked threshold"
    assert tab.beat_asmr_visuals_edit.text() == "floating dust, trembling curtain"
    assert tab.beat_composition_edit.text() == "small figure framed by a tall doorway"
    assert tab.beat_posture_edit.text() == "hand on door, shoulders raised"
    assert tab.beat_expression_edit.text() == "anxious eyes"
    assert tab.beat_body_language_edit.text() == "hesitant forward lean"
    assert tab.beat_props_edit.text() == "old key"
    assert tab.beat_wardrobe_notes_edit.text() == "black jacket damp from rain"
    assert tab.beat_character_state_edit.text() == "tired but alert"
    assert tab.beat_location_state_edit.text() == "abandoned house disturbed"
    assert tab.beat_transition_note_edit.text() == "from rain outside to dark hallway"
    assert "Lam Vu - young" in tab.beat_character_variants_edit.text()
    assert "Blue gray inner robe" in tab.beat_character_outfits_edit.text()


def test_episode_planner_save_beat_text_changes_saves_all_storyboard_fields():
    project, project_service, chapter = _sample_project()
    ManualAIEpisodePlannerService(project_service).apply_episode_plan_with_review_result(
        project,
        _planner_result(chapter.chapter_id),
    )
    tab, app_state = _build_tab(project, project_service, chapter)
    app_state.selected_episode_id = "ep_ui_001"
    tab.refresh()

    beat_item = tab.scene_tree.topLevelItem(0).child(0)
    tab.scene_tree.setCurrentItem(beat_item)
    tab._on_structure_item_select()

    beat = project.review_episodes[0].scenes[0].beats[0]
    beat.image_prompt = "keep prompt"
    beat.negative_prompt = "keep negative"

    tab.beat_story_function_edit.setText("reveal")
    tab.beat_order_index_edit.setText("3")
    tab.beat_camera_edit.setText("locked static camera")
    tab.beat_time_of_day_edit.setText("Dusk")
    tab.beat_lighting_edit.setText("orange last light")
    tab.beat_atmosphere_edit.setText("uneasy quiet air")
    tab.beat_location_cues_edit.setText("broken steps, wet footprints")
    tab.beat_asmr_visuals_edit.setText("rain beads, swaying cobweb")
    tab.beat_composition_edit.setText("door centered, character at lower edge")
    tab.beat_posture_edit.setText("half crouched")
    tab.beat_expression_edit.setText("fear mixed with resolve")
    tab.beat_body_language_edit.setText("one hand clenched")
    tab.beat_props_edit.setText("key, letter")
    tab.beat_wardrobe_notes_edit.setText("jacket torn at sleeve")
    tab.beat_character_state_edit.setText("injured but focused")
    tab.beat_location_state_edit.setText("freshly disturbed entryway")
    tab.beat_transition_note_edit.setText("leads into the hidden letter reveal")
    tab.beat_character_variants_edit.setText("LÃ¢m VÅ© -> Lam Vu - old")
    tab.beat_character_outfits_edit.setText("LÃ¢m VÅ© -> Torn battle robe")
    tab._on_save_beat_text_changes()

    assert beat.story_function == "reveal"
    assert beat.order_index == 3
    assert beat.camera == "locked static camera"
    assert beat.timeOfDay == "Dusk"
    assert beat.lighting == "orange last light"
    assert beat.atmosphere == "uneasy quiet air"
    assert beat.location_cues == "broken steps, wet footprints"
    assert beat.asmr_visuals == "rain beads, swaying cobweb"
    assert beat.composition == "door centered, character at lower edge"
    assert beat.posture == "half crouched"
    assert beat.expression == "fear mixed with resolve"
    assert beat.body_language == "one hand clenched"
    assert beat.props == ["key", "letter"]
    assert beat.wardrobe_notes == "jacket torn at sleeve"
    assert beat.character_state == "injured but focused"
    assert beat.location_state == "freshly disturbed entryway"
    assert beat.transition_note == "leads into the hidden letter reveal"
    assert beat.character_variants == {"lam_vu": "lam_vu_old"}
    assert beat.character_outfits == {"lam_vu": "outfit_lam_vu_old_battle"}
    assert beat.image_prompt == "keep prompt"
    assert beat.negative_prompt == "keep negative"


def test_episode_planner_apply_json_refreshes_preview():
    project, project_service, chapter = _sample_project()
    tab, _ = _build_tab(project, project_service, chapter)
    tab.chapter_list.item(0).setSelected(True)
    tab.result_input.setPlainText(json.dumps(_planner_result(chapter.chapter_id), ensure_ascii=False))

    with patch("app.ui.episode_planner_tab.QMessageBox.information"):
        tab._on_import_plan()

    assert tab.scene_tree.topLevelItemCount() == 2
    assert "Beat 1" in tab.scene_tree.topLevelItem(0).child(0).text(0)
    assert "Đã tạo/cập nhật" in tab.apply_summary_label.text()


def test_beat_studio_can_consume_episode_planner_output():
    project, project_service, chapter = _sample_project()
    ManualAIEpisodePlannerService(project_service).apply_episode_plan_with_review_result(
        project,
        _planner_result(chapter.chapter_id),
    )
    app_state = AppState(project=project, selected_episode_id="ep_ui_001")
    beat_studio = BeatStudioTab(
        app_state,
        GenerationController(project_service),
        ManualAIController(project_service),
        Mock(),
    )

    beat_studio.refresh()

    assert beat_studio.scene_list.count() == 2
    assert beat_studio._beat_count() == 2


def test_episode_planner_structure_preview_uses_collapsible_tree():
    project, project_service, chapter = _sample_project()
    tab, _ = _build_tab(project, project_service, chapter)
    assert hasattr(tab, "scene_tree")
    assert tab.scene_tree.columnCount() == 4


def test_episode_planner_scenes_collapsed_by_default():
    project, project_service, chapter = _sample_project()
    ManualAIEpisodePlannerService(project_service).apply_episode_plan_with_review_result(
        project, _planner_result(chapter.chapter_id)
    )
    tab, app_state = _build_tab(project, project_service, chapter)
    app_state.selected_episode_id = "ep_ui_001"
    app_state.selected_scene_id = None
    tab.refresh()

    assert tab.scene_tree.topLevelItemCount() == 2
    assert not tab.scene_tree.topLevelItem(0).isExpanded()
    assert not tab.scene_tree.topLevelItem(1).isExpanded()


def test_click_scene_expands_beats():
    project, project_service, chapter = _sample_project()
    ManualAIEpisodePlannerService(project_service).apply_episode_plan_with_review_result(
        project, _planner_result(chapter.chapter_id)
    )
    tab, app_state = _build_tab(project, project_service, chapter)
    app_state.selected_episode_id = "ep_ui_001"
    tab.refresh()

    scene_item = tab.scene_tree.topLevelItem(0)
    tab.scene_tree.itemClicked.emit(scene_item, 0)
    assert scene_item.isExpanded()


def test_click_scene_again_collapses_beats():
    project, project_service, chapter = _sample_project()
    ManualAIEpisodePlannerService(project_service).apply_episode_plan_with_review_result(
        project, _planner_result(chapter.chapter_id)
    )
    tab, app_state = _build_tab(project, project_service, chapter)
    app_state.selected_episode_id = "ep_ui_001"
    tab.refresh()

    scene_item = tab.scene_tree.topLevelItem(0)
    tab.scene_tree.itemClicked.emit(scene_item, 0) # Expand
    assert scene_item.isExpanded()
    tab.scene_tree.itemClicked.emit(scene_item, 0) # Collapse
    assert not scene_item.isExpanded()


def test_only_selected_scene_expanded():
    project, project_service, chapter = _sample_project()
    ManualAIEpisodePlannerService(project_service).apply_episode_plan_with_review_result(
        project, _planner_result(chapter.chapter_id)
    )
    tab, app_state = _build_tab(project, project_service, chapter)
    app_state.selected_episode_id = "ep_ui_001"
    tab.refresh()

    scene1 = tab.scene_tree.topLevelItem(0)
    scene2 = tab.scene_tree.topLevelItem(1)

    tab.scene_tree.itemClicked.emit(scene1, 0)
    assert scene1.isExpanded()
    assert not scene2.isExpanded()

    tab.scene_tree.itemClicked.emit(scene2, 0)
    assert scene2.isExpanded()
    assert not scene1.isExpanded()


def test_click_beat_loads_selected_beat_details():
    project, project_service, chapter = _sample_project()
    ManualAIEpisodePlannerService(project_service).apply_episode_plan_with_review_result(
        project, _planner_result(chapter.chapter_id)
    )
    tab, app_state = _build_tab(project, project_service, chapter)
    app_state.selected_episode_id = "ep_ui_001"
    tab.refresh()

    scene_item = tab.scene_tree.topLevelItem(0)
    beat_item = scene_item.child(0)
    tab.scene_tree.setCurrentItem(beat_item)
    tab._on_structure_item_select()

    assert app_state.selected_beat_id == "beat_sc_001_001"
    assert tab.beat_action_edit.text() == "Lâm Vũ opens the old door."


def test_refresh_preserves_expanded_selected_scene():
    project, project_service, chapter = _sample_project()
    ManualAIEpisodePlannerService(project_service).apply_episode_plan_with_review_result(
        project, _planner_result(chapter.chapter_id)
    )
    tab, app_state = _build_tab(project, project_service, chapter)
    app_state.selected_episode_id = "ep_ui_001"
    app_state.selected_scene_id = "sc_001"
    tab.refresh()

    scene_item = tab.scene_tree.topLevelItem(0)
    assert scene_item.isExpanded()


def test_scene_rows_show_beat_count():
    project, project_service, chapter = _sample_project()
    ManualAIEpisodePlannerService(project_service).apply_episode_plan_with_review_result(
        project, _planner_result(chapter.chapter_id)
    )
    tab, app_state = _build_tab(project, project_service, chapter)
    app_state.selected_episode_id = "ep_ui_001"
    tab.refresh()

    scene_item = tab.scene_tree.topLevelItem(0)
    assert "2 beats" in scene_item.text(0)


def test_scene_and_beat_rows_use_names_not_raw_ids():
    project, project_service, chapter = _sample_project()
    ManualAIEpisodePlannerService(project_service).apply_episode_plan_with_review_result(
        project, _planner_result(chapter.chapter_id)
    )
    # Ensure character name is resolved
    tab, app_state = _build_tab(project, project_service, chapter)
    app_state.selected_episode_id = "ep_ui_001"
    tab.refresh()

    scene_item = tab.scene_tree.topLevelItem(0)
    # Character ID is "lam_vu", Name is "Lâm Vũ"
    assert "Lâm Vũ" in scene_item.text(0)
    assert "lam_vu" not in scene_item.text(0)


def test_episode_planner_scene_rows_are_first_column_spanned():
    project, project_service, chapter = _sample_project()
    ManualAIEpisodePlannerService(project_service).apply_episode_plan_with_review_result(
        project, _planner_result(chapter.chapter_id)
    )
    tab, app_state = _build_tab(project, project_service, chapter)
    app_state.selected_episode_id = "ep_ui_001"
    tab.refresh()

    scene_item = tab.scene_tree.topLevelItem(0)
    assert scene_item.isFirstColumnSpanned()


def test_episode_planner_beat_rows_not_spanned():
    project, project_service, chapter = _sample_project()
    ManualAIEpisodePlannerService(project_service).apply_episode_plan_with_review_result(
        project, _planner_result(chapter.chapter_id)
    )
    tab, app_state = _build_tab(project, project_service, chapter)
    app_state.selected_episode_id = "ep_ui_001"
    tab.refresh()

    scene_item = tab.scene_tree.topLevelItem(0)
    beat_item = scene_item.child(0)
    assert not beat_item.isFirstColumnSpanned()


def test_episode_planner_scene_row_contains_full_scene_title():
    project, project_service, chapter = _sample_project()
    result = _planner_result(chapter.chapter_id)
    result["scenes"][0]["title"] = "This is a very long scene title that should not be truncated in the tree view"
    ManualAIEpisodePlannerService(project_service).apply_episode_plan_with_review_result(project, result)
    
    tab, app_state = _build_tab(project, project_service, chapter)
    app_state.selected_episode_id = "ep_ui_001"
    tab.refresh()

    scene_item = tab.scene_tree.topLevelItem(0)
    assert "This is a very long scene title that should not be truncated" in scene_item.text(0)


def test_episode_planner_scene_row_tooltip_contains_full_metadata():
    project, project_service, chapter = _sample_project()
    ManualAIEpisodePlannerService(project_service).apply_episode_plan_with_review_result(
        project, _planner_result(chapter.chapter_id)
    )
    tab, app_state = _build_tab(project, project_service, chapter)
    app_state.selected_episode_id = "ep_ui_001"
    tab.refresh()

    scene_item = tab.scene_tree.topLevelItem(0)
    tooltip = scene_item.toolTip(0)
    assert "Phân cảnh: Front Door" in tooltip
    assert "Số nhịp: 2" in tooltip
    assert "Nhân vật: Lâm Vũ" in tooltip
    assert "Địa điểm: Old House" in tooltip


def test_episode_planner_beat_columns_still_populated():
    project, project_service, chapter = _sample_project()
    ManualAIEpisodePlannerService(project_service).apply_episode_plan_with_review_result(
        project, _planner_result(chapter.chapter_id)
    )
    tab, app_state = _build_tab(project, project_service, chapter)
    app_state.selected_episode_id = "ep_ui_001"
    tab.refresh()

    scene_item = tab.scene_tree.topLevelItem(0)
    beat_item = scene_item.child(0)
    
    assert "Beat 1:" in beat_item.text(0)
    assert beat_item.text(1) == "hook"
    assert beat_item.text(2) == "tense"
    assert beat_item.text(3) == "wide shot"
