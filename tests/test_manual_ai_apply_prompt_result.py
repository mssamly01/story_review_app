import pytest
from app.services.project_service import ProjectService
from app.services.manual_ai_service import ManualAIService
from app.domain.beat import Beat


@pytest.fixture
def ps():
    return ProjectService()


@pytest.fixture
def project(ps):
    p = ps.create_project("Test Project")
    ep = ps.add_review_episode(p, title="Episode 1", source_chapter_ids=[])
    
    # Scene 1 with 2 beats
    sc1 = ps.add_scene(p, episode_id=ep.episode_id, title="Scene 1", scene_id="sc_001")
    ps.add_beat(p, episode_id=ep.episode_id, scene_id=sc1.scene_id, action="Action 1", beat_id="b1")
    ps.add_beat(p, episode_id=ep.episode_id, scene_id=sc1.scene_id, action="Action 2", beat_id="b2")
    
    # Scene 2 with 1 beat
    sc2 = ps.add_scene(p, episode_id=ep.episode_id, title="Scene 2", scene_id="sc_002")
    ps.add_beat(p, episode_id=ep.episode_id, scene_id=sc2.scene_id, action="Action 3", beat_id="b3")
    
    return p


def test_apply_prompt_result_updates_beats_across_all_scenes(ps, project):
    service = ManualAIService(ps)
    result_data = {
        "prompts": [
            {"beat_id": "b1", "image_prompt": "Prompt 1", "negative_prompt": "Neg 1"},
            {"beat_id": "b3", "image_prompt": "Prompt 3", "negative_prompt": "Neg 3"}
        ]
    }
    
    # Even if sc_001 is "selected", b3 (in sc_002) should be updated
    message = service.import_result(
        project,
        step="build-prompts",
        result_data=result_data,
        episode_id=project.review_episodes[0].episode_id,
        chapter_id="sc_001"
    )
    
    assert "Đã cập nhật prompt cho 2 nhịp trong 2 phân cảnh" in message
    
    ep = project.review_episodes[0]
    b1 = next(b for s in ep.scenes for b in s.beats if b.beat_id == "b1")
    b3 = next(b for s in ep.scenes for b in s.beats if b.beat_id == "b3")
    
    assert b1.image_prompt == "Prompt 1"
    assert b3.image_prompt == "Prompt 3"


def test_apply_prompt_result_nested_scenes(ps, project):
    service = ManualAIService(ps)
    result_data = {
        "scenes": [
            {
                "scene_id": "sc_001",
                "beats": [{"beat_id": "b2", "image_prompt": "Prompt 2"}]
            }
        ]
    }
    
    service.import_result(
        project,
        step="build-prompts",
        result_data=result_data,
        episode_id=project.review_episodes[0].episode_id
    )
    
    ep = project.review_episodes[0]
    b2 = next(b for s in ep.scenes for b in s.beats if b.beat_id == "b2")
    assert b2.image_prompt == "Prompt 2"


def test_apply_prompt_result_preserves_review_text(ps, project):
    service = ManualAIService(ps)
    ep = project.review_episodes[0]
    b1 = next(b for s in ep.scenes for b in s.beats if b.beat_id == "b1")
    b1.review_text = "Original Review"
    
    result_data = {
        "prompts": [{"beat_id": "b1", "image_prompt": "New Prompt"}]
    }
    
    service.import_result(
        project,
        step="build-prompts",
        result_data=result_data,
        episode_id=ep.episode_id
    )
    
    assert b1.review_text == "Original Review"
    assert b1.image_prompt == "New Prompt"


def test_apply_prompt_result_skips_unknown_beats(ps, project):
    service = ManualAIService(ps)
    result_data = {
        "prompts": [
            {"beat_id": "b1", "image_prompt": "Updated"},
            {"beat_id": "unknown_999", "image_prompt": "Ghost"}
        ]
    }
    
    message = service.import_result(
        project,
        step="build-prompts",
        result_data=result_data,
        episode_id=project.review_episodes[0].episode_id
    )
    
    assert "Đã cập nhật prompt cho 1 nhịp" in message
    assert "Bỏ qua 1 nhịp không tìm thấy mã ID" in message

def test_apply_prompt_result_preserves_source_raw_text(ps, project):
    service = ManualAIService(ps)
    ch = ps.add_source_chapter(project, title="Ch 1", chapter_number=1, raw_text="Original Raw Text")
    
    result_data = {
        "prompts": [{"beat_id": "b1", "image_prompt": "New Prompt"}]
    }
    
    service.import_result(
        project,
        step="build-prompts",
        result_data=result_data,
        episode_id=project.review_episodes[0].episode_id
    )
    
    assert ch.raw_text == "Original Raw Text"
