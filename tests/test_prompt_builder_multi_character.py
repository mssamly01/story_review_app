import pytest
from app.domain.project import Project
from app.domain.character import Character, CharacterVariant, CharacterOutfit
from app.domain.beat import Beat
from app.domain.episode import ReviewEpisode
from app.domain.scene import Scene
from app.services.prompt_builder_service import PromptBuilderService

@pytest.fixture
def multi_char_project():
    project = Project(project_id="p1", title="Test Project")
    
    char1 = Character(
        character_id="char_001",
        name="Co Than",
        gender="Male",
        age_description="10 years old",
        visual_prompt_base="10-year-old ancient fantasy boy",
        negative_prompt_terms=["modern", "sci-fi"]
    )
    char1.variants.append(CharacterVariant(
        variant_id="char_001_young",
        character_id="char_001",
        display_name="Young Co Than",
        age_description="appears 10 years old",
        appearance="messy black hair",
        negative_prompt_terms=["old man"]
    ))
    
    char2 = Character(
        character_id="char_002",
        name="Tang Thien Co",
        gender="Male",
        age_description="adult immortal",
        visual_prompt_base="god-like ancient immortal",
        negative_prompt_terms=["weak", "child"]
    )
    char2.variants.append(CharacterVariant(
        variant_id="char_002_adult",
        character_id="char_002",
        display_name="Adult Tang Thien Co",
        appearance="cold noble face",
        negative_prompt_terms=["ugly"]
    ))
    
    project.characters.extend([char1, char2])
    
    episode = ReviewEpisode(episode_id="ep1", title="Ep 1")
    scene = Scene(scene_id="sc1", episode_id="ep1", title="Scene 1", location="Location 1")
    beat = Beat(
        beat_id="b1",
        scene_id="sc1",
        order_index=0,
        characters=["char_001", "char_002"],
        character_variants={
            "char_001": "char_001_young",
            "char_002": "char_002_adult"
        },
        character_states={
            "char_001": {
                "posture": "lying on bed",
                "expression": "confused"
            },
            "char_002": {
                "posture": "standing near doorway",
                "expression": "concerned"
            }
        },
        action="Co Than and Tang Thien Co look at each other."
    )
    scene.beats.append(beat)
    episode.scenes.append(scene)
    project.review_episodes.append(episode)
    
    return project

def test_prompt_builder_describes_all_beat_characters(multi_char_project):
    service = PromptBuilderService()
    beat = multi_char_project.review_episodes[0].scenes[0].beats[0]
    service.build_prompt_for_beat(multi_char_project, "b1")
    
    prompt = beat.image_prompt
    assert "Co Than" in prompt
    assert "Tang Thien Co" in prompt
    assert "lying on bed" in prompt
    assert "standing near doorway" in prompt
    assert "confused" in prompt
    assert "concerned" in prompt

def test_prompt_builder_does_not_only_name_secondary_character(multi_char_project):
    service = PromptBuilderService()
    beat = multi_char_project.review_episodes[0].scenes[0].beats[0]
    service.build_prompt_for_beat(multi_char_project, "b1")
    
    prompt = beat.image_prompt
    # Check that Tang Thien Co (secondary) has a full block with parenthesis
    assert "Tang Thien Co" in prompt
    assert "Visual base: god-like ancient immortal" in prompt

def test_prompt_builder_multiple_characters_uses_selected_variants(multi_char_project):
    service = PromptBuilderService()
    beat = multi_char_project.review_episodes[0].scenes[0].beats[0]
    service.build_prompt_for_beat(multi_char_project, "b1")
    
    prompt = beat.image_prompt
    assert "Young Co Than" in prompt
    assert "Adult Tang Thien Co" in prompt

def test_prompt_builder_no_raw_ids_for_multiple_characters(multi_char_project):
    service = PromptBuilderService()
    beat = multi_char_project.review_episodes[0].scenes[0].beats[0]
    service.build_prompt_for_beat(multi_char_project, "b1")
    
    prompt = beat.image_prompt
    assert "char_001" not in prompt
    assert "char_002" not in prompt

def test_prompt_builder_negative_prompt_includes_all_character_negatives(multi_char_project):
    service = PromptBuilderService()
    beat = multi_char_project.review_episodes[0].scenes[0].beats[0]
    service.build_prompt_for_beat(multi_char_project, "b1")
    
    neg = beat.negative_prompt
    # Terms from char1: modern, sci-fi, old man
    # Terms from char2: weak, child, ugly
    assert "modern" in neg
    assert "sci-fi" in neg
    assert "old man" in neg
    assert "weak" in neg
    assert "child" in neg
    assert "ugly" in neg

def test_prompt_builder_action_describes_interaction(multi_char_project):
    service = PromptBuilderService()
    beat = multi_char_project.review_episodes[0].scenes[0].beats[0]
    service.build_prompt_for_beat(multi_char_project, "b1")
    
    prompt = beat.image_prompt
    assert "Co Than and Tang Thien Co look at each other" in prompt
