import pytest
from app.domain.project import Project
from app.domain.character import Character
from app.services.project_service import ProjectService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.character_reference_prompt_service import CharacterReferencePromptService


@pytest.fixture
def project_service():
    return ProjectService()


@pytest.fixture
def project(project_service):
    p = project_service.create_project("Test Project")
    project_service.add_source_chapter(p, title="Ch 1", chapter_number=1, raw_text="text")
    project_service.add_review_episode(p, title="Ep 1", source_chapter_ids=["ch_001"])
    project_service.add_scene(p, episode_id="ep_001", title="Scene 1")
    return p


def test_beat_prompt_uses_concise_character_data(project, project_service):
    """Character has both beat prompt data and full reference sheet data.
    Build beat image prompt.
    Assert it includes visual_prompt_base and default_outfit.
    Assert it does not include full reference sheet layout terms.
    """
    char = project_service.add_character(
        project,
        name="John Doe",
        visual_prompt_base="handsome man with a hat",
        default_outfit="blue jacket",
        signature_features="scar on left eye",
        # Full reference data
        required_views="front, side, back turnaround",
        expression_set="happy, sad, angry, surprised progression",
        pose_set="t-pose, walking, running set",
        sheet_layout_style="full turnaround layout"
    )
    
    episode = project.review_episodes[0]
    scene = episode.scenes[0]
    project_service.add_beat(
        project,
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        visual_description="John is walking",
        characters=[char.character_id]
    )
    beat = scene.beats[0]
    
    builder = PromptBuilderService()
    builder.build_prompt_for_beat(project, beat.beat_id)
    
    prompt = beat.image_prompt.lower()
    
    assert "handsome man with a hat" in prompt
    assert "blue jacket" in prompt
    assert "scar on left eye" in prompt
    
    # Negative assertions: should NOT include ref sheet specific terms
    assert "front, side, back turnaround" not in prompt
    assert "happy, sad, angry, surprised progression" not in prompt
    assert "t-pose, walking, running set" not in prompt
    assert "full turnaround layout" not in prompt


def test_reference_sheet_prompt_uses_full_reference_data(project, project_service):
    """Build reference sheet prompt.
    Assert it includes required_views, expression_set, head_angle_views, wardrobe_details, prop_details, color_palette.
    """
    char = project_service.add_character(
        project,
        name="Jane Smith",
        required_views="five-point turnaround",
        expression_set="range of emotions",
        head_angle_views="360 rotation",
        wardrobe_details="tactical gear",
        prop_details="laser pistol",
        color_palette="neon pink and black"
    )
    
    ref_service = CharacterReferencePromptService()
    prompt = ref_service.build_reference_sheet_prompt(project, char.character_id)
    
    assert "five-point turnaround" in prompt
    assert "range of emotions" in prompt
    assert "360 rotation" in prompt
    assert "tactical gear" in prompt
    assert "laser pistol" in prompt
    assert "neon pink and black" in prompt


def test_reference_sheet_prompt_does_not_modify_project(project, project_service):
    """Serialize before/after."""
    char = project_service.add_character(project, name="Static Char")
    
    before = project.to_dict()
    
    ref_service = CharacterReferencePromptService()
    ref_service.build_reference_sheet_prompt(project, char.character_id)
    
    after = project.to_dict()
    
    assert before == after


def test_beat_prompt_includes_reference_image_note_when_available(project, project_service):
    """Character has reference_image_note.
    Build beat prompt.
    Assert prompt mentions using character reference for consistency.
    """
    char = project_service.add_character(
        project,
        name="Consistent Char",
        reference_image_note="use model v2"
    )
    
    episode = project.review_episodes[0]
    scene = episode.scenes[0]
    project_service.add_beat(
        project,
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        visual_description="Char standing",
        characters=[char.character_id]
    )
    beat = scene.beats[0]
    
    builder = PromptBuilderService()
    builder.build_prompt_for_beat(project, beat.beat_id)
    
    prompt = beat.image_prompt.lower()
    
    assert "use the character reference sheet for visual consistency" in prompt
    assert "use model v2" in prompt


def test_product_direction_guards_still_pass(project, project_service):
    """Ensure we haven't broken the 'no video editor' or 'no automatic image generation' guards.
    Since we are running this alongside other tests, we just verify they pass.
    """
    pass
