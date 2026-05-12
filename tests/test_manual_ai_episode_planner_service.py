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
from app.services.manual_ai_service import ManualAIService
from app.services.project_service import ProjectService
from app.ui.app_state import AppState
from app.ui.episode_planner_tab import EpisodePlannerTab


def _project_with_context():
    project_service = ProjectService()
    project = project_service.create_project(
        "Long Story",
        genre="mystery",
        language="vi",
        default_narration_style="mysterious",
        default_art_style="style_dark",
    )
    chapter = project_service.add_source_chapter(
        project,
        title="Chapter One",
        chapter_number=1,
        raw_text="Lâm Vũ bước vào căn nhà cũ và phát hiện một lá thư bị giấu dưới sàn.",
    )
    project_service.add_character(
        project,
        character_id="char_lam_vu",
        name="Lâm Vũ",
        visual_prompt_base="young man with messy black hair",
        default_outfit="black jacket",
    )
    project_service.add_location(
        project,
        location_id="loc_old_house",
        name="Old House",
        visual_prompt_base="dusty old countryside house",
        lighting="dim moonlight",
    )
    project_service.add_style_preset(
        project,
        style_id="style_dark",
        name="Dark Webtoon",
        positive_prompt="cinematic dark webtoon style",
        negative_prompt="low quality, blurry, text, watermark, logo",
    )
    return project, project_service, chapter


def _episode_result(chapter_id: str) -> dict:
    return {
        "episode": {
            "episode_id": "ep_manual_001",
            "title": "Episode Manual",
            "summary": "Lâm Vũ enters the old house.",
            "hook": "A hidden letter changes everything.",
            "cliffhanger": "Someone is watching him.",
            "source_chapter_ids": [chapter_id],
            "narration_style": "mysterious",
            "retelling_density": "full",
        },
        "scenes": [
            {
                "scene_id": "sc_001",
                "title": "The Door",
                "summary": "Lâm Vũ arrives at the house.",
                "mood": "tense",
                "characters": ["char_lam_vu"],
                "location": "loc_old_house",
                "target_beats": 2,
                "beats": [
                    {
                        "beat_id": "beat_sc_001_001",
                        "scene_id": "sc_001",
                        "order_index": 1,
                        "story_function": "hook",
                        "characters": ["char_lam_vu"],
                        "location": "loc_old_house",
                        "action": "Lâm Vũ pushes the old door open.",
                        "emotion": "tense",
                        "shot_type": "wide shot",
                        "visual_description": "He stands at the doorway under dim light.",
                        "review_text": "Lúc này, Lâm Vũ chậm rãi đẩy cánh cửa cũ ra, cảm giác bất an bắt đầu bám lấy từng bước chân của anh.",
                        "continuity_tags": ["old house", "hidden letter"],
                    },
                    {
                        "beat_id": "beat_sc_001_002",
                        "scene_id": "sc_001",
                        "order_index": 2,
                        "story_function": "discovery",
                        "characters": ["char_lam_vu"],
                        "location": "loc_old_house",
                        "action": "He finds a hidden letter below the floor.",
                        "emotion": "shocked",
                        "shot_type": "close-up",
                        "visual_description": "His hand lifts a dusty loose board.",
                        "review_text": "Ngay dưới tấm ván phủ bụi, anh phát hiện một lá thư bị giấu kín, như thể ai đó đã cố tình để nó chờ đúng người tìm thấy.",
                        "continuity_tags": ["old house", "letter"],
                    },
                ],
            },
            {
                "scene_id": "sc_002",
                "title": "The Letter",
                "summary": "The letter hints at a watcher.",
                "mood": "suspicious",
                "characters": ["char_lam_vu"],
                "location": "loc_old_house",
                "target_beats": 1,
                "beats": [
                    {
                        "beat_id": "beat_sc_002_001",
                        "scene_id": "sc_002",
                        "order_index": 1,
                        "story_function": "reveal",
                        "characters": ["char_lam_vu"],
                        "location": "loc_old_house",
                        "action": "He reads the warning inside the letter.",
                        "emotion": "fearful",
                        "shot_type": "detail shot",
                        "visual_description": "The warning is reflected in his eyes.",
                        "review_text": "Khi đọc những dòng cảnh báo đầu tiên, Lâm Vũ hiểu rằng chuyến đi này không hề tình cờ.",
                        "continuity_tags": ["letter", "warning"],
                    }
                ],
            },
        ],
    }


def _long_project_with_context():
    project, project_service, _chapter = _project_with_context()
    project.source_chapters.clear()
    long_events = []
    for index in range(420):
        long_events.append(
            f"Event {index}: Lam Vu loses something, remembers a painful flashback, "
            "makes a vow, discovers a clue, and faces an emotional turn."
        )
    chapter = project_service.add_source_chapter(
        project,
        title="Dense Long Chapter",
        chapter_number=9,
        raw_text=" ".join(long_events),
        chapter_id="ch_long_001",
    )
    return project, project_service, chapter


def _episode_result_with_beat_count(chapter_id: str, beat_count: int, density: str = "full") -> dict:
    beats = []
    for index in range(1, beat_count + 1):
        beats.append(
            {
                "beat_id": f"beat_sc_001_{index:03d}",
                "scene_id": "sc_001",
                "order_index": index,
                "story_function": "discovery",
                "characters": ["char_lam_vu"],
                "location": "loc_old_house",
                "action": f"Story moment {index}",
                "emotion": "tense",
                "shot_type": "medium shot",
                "visual_description": f"Visual focus for moment {index}",
                "review_text": (
                    "Lâm Vũ tiếp tục đi qua một biến cố quan trọng, và nhịp kể "
                    "giữ lại nguyên nhân, cảm xúc cùng hậu quả của khoảnh khắc này."
                ),
                "continuity_tags": [f"moment_{index}"],
            }
        )
    return {
        "episode": {
            "episode_id": "ep_dense_001",
            "title": "Dense Episode",
            "summary": "A dense chapter retold in detail.",
            "source_chapter_ids": [chapter_id],
            "narration_style": "mysterious",
            "retelling_density": density,
        },
        "scenes": [
            {
                "scene_id": "sc_001",
                "title": "Dense Sequence",
                "summary": "A long chain of emotional story turns.",
                "mood": "tense",
                "characters": ["char_lam_vu"],
                "location": "loc_old_house",
                "scene_type": "flashback",
                "importance": "critical",
                "target_beats": beat_count,
                "beats": beats,
            }
        ],
    }


def test_episode_planner_prompt_contains_scene_beat_review_tasks():
    project, _, chapter = _project_with_context()
    prompt = ManualAIEpisodePlannerService().build_episode_plan_with_review_prompt(
        project,
        [chapter.chapter_id],
    )

    assert "screens/scenes" in prompt
    assert "beats" in prompt
    assert "review_text" in prompt
    assert "Vietnamese voice-over" in prompt


def test_episode_planner_prompt_includes_long_form_not_summary_rule():
    project, _, chapter = _project_with_context()

    prompt = ManualAIEpisodePlannerService().build_episode_plan_with_review_prompt(
        project,
        [chapter.chapter_id],
    )

    assert "not a summary app" in prompt
    assert "Do not over-summarize" in prompt


def test_episode_planner_prompt_includes_density_targets():
    project, _, chapter = _project_with_context()
    service = ManualAIEpisodePlannerService()

    full_prompt = service.build_episode_plan_with_review_prompt(
        project,
        [chapter.chapter_id],
        retelling_density="full",
    )
    ultra_prompt = service.build_episode_plan_with_review_prompt(
        project,
        [chapter.chapter_id],
        retelling_density="ultra_detailed",
    )

    assert "80-110 beats" in full_prompt
    assert "110-150 beats" in ultra_prompt
    assert '"requested_retelling_density": "ultra_detailed"' in ultra_prompt


def test_episode_planner_prompt_includes_minimum_for_long_chapter():
    project, _, chapter = _long_project_with_context()

    prompt = ManualAIEpisodePlannerService().build_episode_plan_with_review_prompt(
        project,
        [chapter.chapter_id],
        retelling_density="full",
    )

    assert "do not output fewer than 60 beats unless density is short" in prompt
    assert '"is_long_source": true' in prompt


def test_episode_planner_prompt_includes_scene_type_target_beat_guidance():
    project, _, chapter = _project_with_context()

    prompt = ManualAIEpisodePlannerService().build_episode_plan_with_review_prompt(
        project,
        [chapter.chapter_id],
    )

    assert "flashback/life-history scene: 10-15 beats" in prompt
    assert "tragedy scene: 8-12 beats" in prompt
    assert "emotional scene: 5-8 beats" in prompt


def test_episode_planner_output_schema_includes_scene_type_importance_target_beats():
    project, _, chapter = _project_with_context()

    prompt = ManualAIEpisodePlannerService().build_episode_plan_with_review_prompt(
        project,
        [chapter.chapter_id],
    )

    assert '"scene_type"' in prompt
    assert '"importance"' in prompt
    assert '"target_beats"' in prompt


def test_episode_planner_prompt_includes_source_text():
    project, _, chapter = _project_with_context()
    prompt = ManualAIEpisodePlannerService().build_episode_plan_with_review_prompt(
        project,
        [chapter.chapter_id],
    )

    assert chapter.raw_text in prompt
    assert chapter.title in prompt


def test_episode_planner_prompt_includes_bible_style_context():
    project, _, chapter = _project_with_context()
    prompt = ManualAIEpisodePlannerService().build_episode_plan_with_review_prompt(
        project,
        [chapter.chapter_id],
    )

    assert "young man with messy black hair" in prompt
    assert "dusty old countryside house" in prompt
    assert "cinematic dark webtoon style" in prompt


def test_episode_planner_prompt_excludes_image_prompt_by_default():
    project, _, chapter = _project_with_context()
    prompt = ManualAIEpisodePlannerService().build_episode_plan_with_review_prompt(
        project,
        [chapter.chapter_id],
    )

    assert "Do not generate image_prompt" in prompt
    assert "Do not generate negative_prompt" in prompt


def test_episode_planner_apply_warns_when_full_density_too_few_beats():
    project, project_service, chapter = _long_project_with_context()

    summary = ManualAIEpisodePlannerService(
        project_service
    ).apply_episode_plan_with_review_result(
        project,
        _episode_result_with_beat_count(chapter.chapter_id, 25, density="full"),
    )

    assert summary["beat_count"] == 25
    assert summary["warnings"]
    assert "80-110 beat" in summary["warnings"][0]


def test_episode_planner_apply_accepts_high_density_result():
    project, project_service, chapter = _long_project_with_context()

    summary = ManualAIEpisodePlannerService(
        project_service
    ).apply_episode_plan_with_review_result(
        project,
        _episode_result_with_beat_count(chapter.chapter_id, 80, density="full"),
    )

    assert summary["beat_count"] == 80
    assert summary["warnings"] == []


def test_apply_episode_plan_with_review_creates_scenes_and_beats():
    project, project_service, chapter = _project_with_context()
    result = _episode_result(chapter.chapter_id)

    summary = ManualAIEpisodePlannerService(
        project_service
    ).apply_episode_plan_with_review_result(project, result)

    assert summary["scene_count"] == 2
    assert summary["beat_count"] == 3
    episode = project.review_episodes[0]
    assert episode.episode_id == "ep_manual_001"
    assert len(episode.scenes) == 2
    assert all(beat.review_text for scene in episode.scenes for beat in scene.beats)
    assert all(beat.image_prompt == "" for scene in episode.scenes for beat in scene.beats)
    assert all(beat.negative_prompt == "" for scene in episode.scenes for beat in scene.beats)


def test_apply_episode_plan_groups_beats_by_scene_id():
    project, project_service, chapter = _project_with_context()
    ManualAIEpisodePlannerService(project_service).apply_episode_plan_with_review_result(
        project,
        _episode_result(chapter.chapter_id),
    )

    episode = project.review_episodes[0]
    sc_001 = next(scene for scene in episode.scenes if scene.scene_id == "sc_001")
    sc_002 = next(scene for scene in episode.scenes if scene.scene_id == "sc_002")

    assert [beat.scene_id for beat in sc_001.beats] == ["sc_001", "sc_001"]
    assert [beat.beat_id for beat in sc_002.beats] == ["beat_sc_002_001"]


def test_apply_episode_plan_updates_existing_without_duplicates():
    project, project_service, chapter = _project_with_context()
    service = ManualAIEpisodePlannerService(project_service)
    result = _episode_result(chapter.chapter_id)

    service.apply_episode_plan_with_review_result(project, result)
    service.apply_episode_plan_with_review_result(project, result)

    episode = project.review_episodes[0]
    scene_ids = [scene.scene_id for scene in episode.scenes]
    beat_ids = [beat.beat_id for scene in episode.scenes for beat in scene.beats]

    assert len(scene_ids) == len(set(scene_ids))
    assert len(beat_ids) == len(set(beat_ids))
    assert len(beat_ids) == 3


def test_apply_episode_plan_preserves_source_raw_text():
    project, project_service, chapter = _project_with_context()
    original_raw_text = chapter.raw_text

    ManualAIEpisodePlannerService(project_service).apply_episode_plan_with_review_result(
        project,
        _episode_result(chapter.chapter_id),
    )

    assert chapter.raw_text == original_raw_text


def test_manual_ai_service_supports_episode_plan_with_review_step():
    project, project_service, chapter = _project_with_context()
    service = ManualAIService(project_service)

    prompt = service.format_prompt_for_clipboard(
        service.export_prompt(
            project,
            step="plan-episode-with-review",
            chapter_ids=[chapter.chapter_id],
        )
    )
    message = service.import_result(
        project,
        step="plan-episode-with-review",
        result_data=_episode_result(chapter.chapter_id),
    )

    assert "review_text" in prompt
    assert "nhịp truyện" in message
    assert project.review_episodes[0].scenes[0].beats[0].review_text


def test_episode_planner_apply_refreshes_beat_studio_data_if_controller_level_possible():
    app = QApplication.instance() or QApplication([])
    project, project_service, chapter = _project_with_context()
    app_state = AppState(project=project, selected_chapter_ids=[chapter.chapter_id])
    refresh_callback = Mock()
    tab = EpisodePlannerTab(
        app_state,
        ProjectController(project_service),
        GenerationController(project_service),
        BatchWorkflowController(project_service),
        ManualAIController(project_service),
        refresh_callback,
    )
    tab.refresh()
    tab.chapter_list.item(0).setSelected(True)
    tab.result_input.setPlainText(json.dumps(_episode_result(chapter.chapter_id), ensure_ascii=False))

    with patch("app.ui.episode_planner_tab.QMessageBox.information"):
        tab._on_import_plan()

    assert app is not None
    refresh_callback.assert_called_once()
    episode = project.review_episodes[0]
    assert episode.scenes[0].beats[0].review_text


def test_beat_studio_prompt_only_flow_still_updates_image_prompts():
    project_service = ProjectService()
    project = project_service.create_project("Prompt Flow")
    chapter = project_service.add_source_chapter(
        project,
        title="Chapter",
        chapter_number=1,
        raw_text="Original source text",
    )
    episode = project_service.add_review_episode(
        project,
        title="Episode",
        source_chapter_ids=[chapter.chapter_id],
    )
    scene = project_service.add_scene(
        project,
        episode_id=episode.episode_id,
        scene_id="sc_001",
        title="Scene",
    )
    beat = project_service.add_beat(
        project,
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        beat_id="beat_sc_001_001",
        review_text="Original review text",
    )

    ManualAIService(project_service).import_result(
        project,
        step="build-prompts",
        result_data={
            "prompts": [
                {
                    "beat_id": beat.beat_id,
                    "image_prompt": "English image prompt",
                    "negative_prompt": "low quality, blurry, text, watermark, logo",
                }
            ]
        },
        episode_id=episode.episode_id,
    )

    assert beat.review_text == "Original review text"
    assert beat.image_prompt == "English image prompt"
    assert beat.negative_prompt
    assert chapter.raw_text == "Original source text"
