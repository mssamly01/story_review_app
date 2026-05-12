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
    project_service.add_character(
        project,
        character_id="lam_vu",
        name="Lâm Vũ",
        visual_prompt_base="young man with messy black hair",
    )
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
                        "location": "old_house",
                        "action": "Lâm Vũ opens the old door.",
                        "emotion": "tense",
                        "shot_type": "wide shot",
                        "visual_description": "He stands before the doorway.",
                        "review_text": "Lâm Vũ chậm rãi mở cánh cửa cũ, và cảm giác bất an lập tức bao trùm lấy anh.",
                        "continuity_tags": ["old house", "door"],
                    },
                    {
                        "beat_id": "beat_sc_001_002",
                        "scene_id": "sc_001",
                        "order_index": 2,
                        "story_function": "discovery",
                        "characters": ["lam_vu"],
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
    assert tab.scene_list is not None
    assert not hasattr(tab, "beat_table")
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

    assert tab.scene_list.count() == 5
    assert "Front Door" in tab.scene_list.item(0).text()
    assert "2 beats" in tab.scene_list.item(0).text()
    assert "Beat 1" in tab.scene_list.item(1).text()
    assert "Beat 2" in tab.scene_list.item(2).text()
    assert "Hidden Letter" in tab.scene_list.item(3).text()
    assert "Lâm Vũ" in tab.scene_list.item(1).text()


def test_episode_planner_detail_save_updates_only_story_fields():
    project, project_service, chapter = _sample_project()
    ManualAIEpisodePlannerService(project_service).apply_episode_plan_with_review_result(
        project,
        _planner_result(chapter.chapter_id),
    )
    tab, app_state = _build_tab(project, project_service, chapter)
    app_state.selected_episode_id = "ep_ui_001"
    tab.refresh()
    tab.scene_list.setCurrentRow(1)

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


def test_episode_planner_apply_json_refreshes_preview():
    project, project_service, chapter = _sample_project()
    tab, _ = _build_tab(project, project_service, chapter)
    tab.chapter_list.item(0).setSelected(True)
    tab.result_input.setPlainText(json.dumps(_planner_result(chapter.chapter_id), ensure_ascii=False))

    with patch("app.ui.episode_planner_tab.QMessageBox.information"):
        tab._on_import_plan()

    assert tab.scene_list.count() == 5
    assert "Beat 1" in tab.scene_list.item(1).text()
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
