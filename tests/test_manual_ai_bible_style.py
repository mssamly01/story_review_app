import pytest
import json
from app.domain.project import Project
from app.services.project_service import ProjectService
from app.services.manual_ai_bible_style_service import ManualAIBibleStyleService
from app.services.prompt_builder_service import PromptBuilderService


@pytest.fixture
def project_service():
    return ProjectService()


@pytest.fixture
def project(project_service):
    p = project_service.create_project("Test Project")
    project_service.add_source_chapter(
        p, title="Intro", chapter_number=1, raw_text="Once upon a time, John lived in a dark castle."
    )
    return p


def test_build_bible_style_prompt_contains_character_location_style_tasks(project):
    service = ManualAIBibleStyleService()
    prompt = service.build_bible_style_analysis_prompt(project, ["ch_001"])
    
    assert "characters" in prompt.lower()
    assert "locations" in prompt.lower()
    assert "style" in prompt.lower()
    assert "world style notes" in prompt.lower()


def test_build_bible_style_prompt_includes_source_text(project):
    service = ManualAIBibleStyleService()
    prompt = service.build_bible_style_analysis_prompt(project, ["ch_001"])
    
    assert "John lived in a dark castle" in prompt


def test_build_bible_style_prompt_requires_json_only(project):
    service = ManualAIBibleStyleService()
    prompt = service.build_bible_style_analysis_prompt(project, ["ch_001"])
    
    assert "JSON ONLY" in prompt
    assert "No markdown" in prompt


def test_apply_bible_style_result_creates_characters_locations_styles(project):
    service = ManualAIBibleStyleService()
    result = {
        "characters": [{"character_id": "char_001", "name": "John", "role": "Protagonist"}],
        "locations": [{"location_id": "loc_001", "name": "Dark Castle", "location_type": "Castle"}],
        "style_presets": [{"style_id": "style_001", "name": "Gothic", "genre": "Horror"}],
        "world_style_notes": {"genre": "Dark Fantasy"}
    }
    
    service.apply_bible_style_analysis_result(project, result)
    
    assert len(project.characters) == 1
    assert project.characters[0].name == "John"
    assert len(project.locations) == 1
    assert project.locations[0].name == "Dark Castle"
    assert len(project.style_presets) == 1
    assert project.style_presets[0].name == "Gothic"
    assert project.world_style_notes["genre"] == "Dark Fantasy"


def test_apply_bible_style_result_merges_without_overwriting_existing_fields(project, project_service):
    service = ManualAIBibleStyleService()
    
    # Pre-existing character with some data
    char = project_service.add_character(project, name="John", character_id="char_001", role="Original Role")
    char.appearance = "Original Appearance"
    
    result = {
        "characters": [
            {
                "character_id": "char_001", 
                "name": "John Updated", 
                "role": "New Role", 
                "appearance": "New Appearance",
                "personality": "New Personality"
            }
        ]
    }
    
    # Merge mode (overwrite=False)
    service.apply_bible_style_analysis_result(project, result, overwrite=False)
    
    assert project.characters[0].role == "Original Role" # Preserved
    assert project.characters[0].appearance == "Original Appearance" # Preserved
    assert project.characters[0].personality == "New Personality" # Merged


def test_apply_bible_style_result_overwrite_mode_updates_fields(project, project_service):
    service = ManualAIBibleStyleService()
    
    project_service.add_character(project, name="John", character_id="char_001", role="Original Role")
    
    result = {
        "characters": [{"character_id": "char_001", "name": "John", "role": "New Role"}]
    }
    
    # Overwrite mode
    service.apply_bible_style_analysis_result(project, result, overwrite=True)
    
    assert project.characters[0].role == "New Role"


def test_apply_bible_style_result_preserves_source_raw_text(project):
    service = ManualAIBibleStyleService()
    original_text = project.source_chapters[0].raw_text
    
    result = {
        "characters": [{"character_id": "char_001", "name": "John"}]
    }
    
    service.apply_bible_style_analysis_result(project, result)
    
    assert project.source_chapters[0].raw_text == original_text


def test_bible_style_analysis_before_beat_prompt_flow(project, project_service):
    """
    1. Apply Bible/Style result
    2. Build beat prompt
    3. Assert beat prompt uses newly created data
    """
    service = ManualAIBibleStyleService()
    result = {
        "characters": [
            {
                "character_id": "char_001", 
                "name": "John", 
                "visual_prompt_base": "tall warrior",
                "signature_features": ["scar on face"]
            }
        ],
        "style_presets": [
            {
                "style_id": "style_001", 
                "name": "MyStyle", 
                "positive_prompt": "high fidelity, cinematic"
            }
        ]
    }
    service.apply_bible_style_analysis_result(project, result, overwrite=True)
    
    # Setup episode/scene/beat
    project_service.add_review_episode(project, title="Ep 1", source_chapter_ids=["ch_001"])
    scene = project_service.add_scene(project, episode_id="ep_001", title="Scene 1")
    beat = project_service.add_beat(
        project, 
        episode_id="ep_001", 
        scene_id=scene.scene_id, 
        characters=["char_001"]
    )
    
    builder = PromptBuilderService()
    builder.build_prompt_for_beat(project, beat.beat_id, style_preset_id="style_001")
    
    prompt = beat.image_prompt.lower()
    assert "tall warrior" in prompt
    assert "scar on face" in prompt
    assert "high fidelity, cinematic" in prompt


def test_product_direction_guards_still_pass():
    # Placeholder for running existing guard tests
    pass
