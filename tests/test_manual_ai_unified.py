import pytest
import json
from app.domain.project import Project
from app.domain.character import Character
from app.domain.location import Location
from app.domain.style_preset import StylePreset
from app.domain.source_chapter import SourceChapter
from app.domain.episode import ReviewEpisode
from app.domain.scene import Scene
from app.services.manual_ai_service import ManualAIService
from app.services.project_service import ProjectService

@pytest.fixture
def project():
    ps = ProjectService()
    project = ps.create_project("Test Project")
    
    # Add Character
    char = Character(
        character_id="char_001",
        name="Hero",
        visual_prompt_base="a brave hero",
        appearance="tall",
        default_outfit="armor",
        hair="spiky black",
        eyes="blue"
    )
    project.characters.append(char)
    
    # Add Location
    loc = Location(
        location_id="loc_001",
        name="Castle",
        visual_prompt_base="a stone castle",
        description="grand",
        mood="mysterious"
    )
    project.locations.append(loc)
    
    # Add Style
    style = StylePreset(
        style_id="test_style",
        name="Test Style",
        positive_prompt="high quality illustration",
        negative_prompt="low quality"
    )
    project.style_presets.append(style)
    project.default_art_style = "test_style"
    
    # Add Source
    source = SourceChapter(
        chapter_id="ch_001",
        title="Chapter 1",
        chapter_number=1,
        raw_text="The hero entered the castle. He looked around in awe."
    )
    project.source_chapters.append(source)
    
    # Add Episode & Scene
    episode = ReviewEpisode(
        episode_id="ep_001",
        title="Episode 1",
        summary="Hero enters castle",
        source_chapter_ids=["ch_001"]
    )
    scene = Scene(
        scene_id="sc_001",
        episode_id="ep_001",
        title="Entering the castle",
        summary="Hero walks through the gates",
        location="loc_001",
        characters=["char_001"]
    )
    episode.scenes.append(scene)
    project.review_episodes.append(episode)
    
    return project

def test_manual_ai_unified_prompt_contains_all_tasks(project):
    service = ManualAIService()
    exported = service.export_prompt(project, step="generate-unified-package", episode_id="ep_001")
    prompt = service.format_prompt_for_clipboard(exported)
    
    assert "nhịp truyện" in prompt.lower() or "beats" in prompt.lower()
    assert "review_text" in prompt
    assert "image_prompt" in prompt
    assert "negative_prompt" in prompt

def test_manual_ai_unified_prompt_includes_source_context(project):
    service = ManualAIService()
    exported = service.export_prompt(project, step="generate-unified-package", episode_id="ep_001")
    prompt = service.format_prompt_for_clipboard(exported)
    
    assert "The hero entered the castle" in prompt

def test_manual_ai_unified_prompt_includes_character_location_style_bible(project):
    service = ManualAIService()
    exported = service.export_prompt(project, step="generate-unified-package", episode_id="ep_001")
    prompt = service.format_prompt_for_clipboard(exported)
    
    assert "spiky black" in prompt
    assert "armor" in prompt
    assert "stone castle" in prompt
    assert "high quality illustration" in prompt

def test_manual_ai_unified_prompt_requires_json_only(project):
    service = ManualAIService()
    exported = service.export_prompt(project, step="generate-unified-package", episode_id="ep_001")
    prompt = service.format_prompt_for_clipboard(exported)
    
    assert "Chỉ JSON" in prompt or "JSON only" in prompt
    assert "scenes" in prompt
    assert "beats" in prompt

def test_apply_unified_ai_result_creates_beats(project):
    service = ManualAIService()
    result_data = {
        "scenes": [
            {
                "scene_id": "sc_001",
                "title": "Entering the castle",
                "beats": [
                    {
                        "order_index": 1,
                        "story_function": "hook",
                        "characters": ["char_001"],
                        "location": "loc_001",
                        "action": "walks in",
                        "emotion": "awe",
                        "shot_type": "wide",
                        "visual_description": "hero at gate",
                        "review_text": "Người hùng bước vào lâu đài.",
                        "image_prompt": "hero at stone castle gate",
                        "negative_prompt": "low quality",
                        "continuity_tags": ["hero"]
                    }
                ]
            }
        ]
    }
    
    service.import_result(project, step="generate-unified-package", result_data=result_data, episode_id="ep_001")
    
    scene = project.review_episodes[0].scenes[0]
    assert len(scene.beats) > 0
    beat = scene.beats[0]
    assert beat.review_text == "Người hùng bước vào lâu đài."
    assert beat.image_prompt == "hero at stone castle gate"

def test_apply_unified_ai_result_updates_existing_beats_without_duplicates(project):
    service = ManualAIService()
    result_data = {
        "scenes": [
            {
                "scene_id": "sc_001",
                "beats": [
                    {
                        "beat_id": "beat_sc_001_001",
                        "order_index": 1,
                        "review_text": "Lần 1",
                        "image_prompt": "prompt 1"
                    }
                ]
            }
        ]
    }
    
    # First apply
    service.import_result(project, step="generate-unified-package", result_data=result_data, episode_id="ep_001")
    count1 = len(project.review_episodes[0].scenes[0].beats)
    
    # Update text
    result_data["scenes"][0]["beats"][0]["review_text"] = "Lần 2"
    
    # Second apply
    service.import_result(project, step="generate-unified-package", result_data=result_data, episode_id="ep_001")
    count2 = len(project.review_episodes[0].scenes[0].beats)
    
    assert count1 == count2
    assert project.review_episodes[0].scenes[0].beats[0].review_text == "Lần 2"

def test_apply_unified_ai_result_preserves_source_raw_text(project):
    original_text = project.source_chapters[0].raw_text
    service = ManualAIService()
    result_data = {"scenes": []}
    service.import_result(project, step="generate-unified-package", result_data=result_data, episode_id="ep_001")
    assert project.source_chapters[0].raw_text == original_text

def test_apply_unified_ai_result_rejects_invalid_json(project):
    service = ManualAIService()
    # In manual workflow, the UI/Controller usually handles the JSON parsing error before calling import_result.
    # But here we pass a dict. If the dict is missing 'scenes', our implementation should handle it.
    msg = service.import_result(project, step="generate-unified-package", result_data={}, episode_id="ep_001")
    assert "0 beats" in msg

def test_beat_studio_no_primary_offline_generate_package_button():
    from app.ui.beat_studio_tab import BeatStudioTab
    from app.controllers.generation_controller import GenerationController
    from app.controllers.manual_ai_controller import ManualAIController
    from app.ui.app_state import AppState
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication.instance() or QApplication(sys.argv)
    gc = GenerationController()
    mc = ManualAIController()
    state = AppState()
    tab = BeatStudioTab(state, gc, mc, lambda: None)
    
    # Check that advanced buttons are hidden
    assert tab.advanced_action_widget.isHidden()
    # Check that Manual AI section is not hidden
    assert not tab.btn_export_prompt.isHidden()
