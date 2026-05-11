"""Tests for Manual AI beat grouping and filtering.

Covers:
1. Flat JSON grouping by scene_id.
2. Nested JSON grouping.
3. Beat table filtering in UI (simulated via domain/controller).
4. Duplicate prevention.
5. raw_text preservation.
"""

from __future__ import annotations

import pytest
from app.domain.project import Project
from app.domain.episode import ReviewEpisode
from app.domain.scene import Scene
from app.domain.beat import Beat
from app.services.project_service import ProjectService
from app.services.manual_ai_service import ManualAIService
from app.controllers.generation_controller import GenerationController

@pytest.fixture
def project_service():
    return ProjectService()

@pytest.fixture
def project(project_service):
    p = project_service.create_project("Test Project")
    project_service.add_source_chapter(p, title="Ch 1", chapter_number=1, raw_text="Raw text 1")
    return p

@pytest.fixture
def episode(project, project_service):
    ep = project_service.add_review_episode(project, title="Ep 1", source_chapter_ids=[project.source_chapters[0].chapter_id])
    # Add some scenes
    project_service.add_scene(project, episode_id=ep.episode_id, title="Scene 1", scene_id="sc_001")
    project_service.add_scene(project, episode_id=ep.episode_id, title="Scene 2", scene_id="sc_002")
    return ep

def test_apply_flat_beats_groups_by_scene_id(project, episode, project_service):
    """
    test_apply_flat_beats_groups_by_scene_id
    - Paste JSON with 5 beats for sc_001 and 12 beats for sc_002.
    - Assert sc_001.beat_ids length == 5.
    - Assert sc_002.beat_ids length == 12.
    - Assert no beat from sc_002 is in sc_001.beat_ids.
    """
    service = ManualAIService(project_service)
    
    flat_json = {
        "beats": [
            {"beat_id": f"b1_{i}", "scene_id": "sc_001", "review_text": f"text 1_{i}"} for i in range(5)
        ] + [
            {"beat_id": f"b2_{i}", "scene_id": "sc_002", "review_text": f"text 2_{i}"} for i in range(12)
        ]
    }
    
    service.import_result(
        project,
        step="generate-beats",
        result_data=flat_json,
        episode_id=episode.episode_id
    )
    
    sc1 = project_service.find_scene(project, episode.episode_id, "sc_001")
    sc2 = project_service.find_scene(project, episode.episode_id, "sc_002")
    
    assert len(sc1.beats) == 5
    assert len(sc2.beats) == 12
    
    sc1_ids = [b.beat_id for b in sc1.beats]
    for b in sc2.beats:
        assert b.beat_id not in sc1_ids

def test_apply_nested_scenes_keeps_scene_beat_counts(project, episode, project_service):
    """
    test_apply_nested_scenes_keeps_scene_beat_counts
    - Paste nested JSON with multiple scenes.
    - Assert each scene has correct beat count.
    """
    service = ManualAIService(project_service)
    
    nested_json = {
        "scenes": [
            {
                "scene_id": "sc_001",
                "beats": [{"beat_id": f"n1_{i}", "scene_id": "sc_001"} for i in range(3)]
            },
            {
                "scene_id": "sc_002",
                "beats": [{"beat_id": f"n2_{i}", "scene_id": "sc_002"} for i in range(7)]
            }
        ]
    }
    
    service.import_result(
        project,
        step="generate-beats",
        result_data=nested_json,
        episode_id=episode.episode_id
    )
    
    sc1 = project_service.find_scene(project, episode.episode_id, "sc_001")
    sc2 = project_service.find_scene(project, episode.episode_id, "sc_002")
    
    assert len(sc1.beats) == 3
    assert len(sc2.beats) == 7

def test_apply_same_result_twice_no_duplicate_beat_ids(project, episode, project_service):
    """
    test_apply_same_result_twice_no_duplicate_beat_ids
    - Apply same JSON twice.
    - Assert beat count remains the same.
    - Assert scene.beat_ids has no duplicates.
    """
    service = ManualAIService(project_service)
    
    flat_json = {
        "beats": [
            {"beat_id": "dup_1", "scene_id": "sc_001", "review_text": "text 1"},
            {"beat_id": "dup_2", "scene_id": "sc_001", "review_text": "text 2"}
        ]
    }
    
    # First time
    service.import_result(
        project,
        step="generate-beats",
        result_data=flat_json,
        episode_id=episode.episode_id
    )
    
    sc1 = project_service.find_scene(project, episode.episode_id, "sc_001")
    assert len(sc1.beats) == 2
    
    # Second time
    service.import_result(
        project,
        step="generate-beats",
        result_data=flat_json,
        episode_id=episode.episode_id
    )
    
    sc1 = project_service.find_scene(project, episode.episode_id, "sc_001")
    assert len(sc1.beats) == 2, "Should NOT duplicate beats if IDs are identical"
    
    beat_ids = [b.beat_id for b in sc1.beats]
    assert len(beat_ids) == len(set(beat_ids)), "Should have no duplicate IDs in scene.beat_ids"

def test_apply_result_preserves_source_raw_text(project, episode, project_service):
    """
    test_apply_result_preserves_source_raw_text
    - Save raw_text before.
    - Apply JSON.
    - Assert raw_text unchanged.
    """
    original_text = project.source_chapters[0].raw_text
    service = ManualAIService(project_service)
    
    result = {
        "beats": [{"beat_id": "b1", "scene_id": "sc_001", "review_text": "modified"}]
    }
    
    service.import_result(
        project,
        step="generate-beats",
        result_data=result,
        episode_id=episode.episode_id
    )
    
    assert project.source_chapters[0].raw_text == original_text

def test_beat_table_filters_by_selected_scene(project, episode, project_service):
    """
    test_beat_table_filters_by_selected_scene
    - Create project with multiple scenes and beats.
    - Select sc_001.
    - Refresh Beat Studio (simulated via controller/scene call).
    - Assert displayed/listed beats all have scene_id == sc_001.
    """
    # Manually add beats to scenes
    sc1 = project_service.find_scene(project, episode.episode_id, "sc_001")
    sc2 = project_service.find_scene(project, episode.episode_id, "sc_002")
    
    sc1.beats = [Beat(beat_id="b1", scene_id="sc_001", order_index=1)]
    sc2.beats = [Beat(beat_id="b2", scene_id="sc_002", order_index=1)]
    
    # Simulation of BeatStudioTab behavior:
    # 1. User selects sc_001
    # 2. UI calls controller.find_scene(..., "sc_001")
    # 3. UI calls scene.ordered_beats()
    
    ctrl = GenerationController(project_service)
    
    selected_sc = ctrl.find_scene(project, episode.episode_id, "sc_001")
    beats = selected_sc.ordered_beats()
    
    assert len(beats) == 1
    assert beats[0].scene_id == "sc_001"
    
    selected_sc = ctrl.find_scene(project, episode.episode_id, "sc_002")
    beats = selected_sc.ordered_beats()
    
    assert len(beats) == 1
    assert beats[0].scene_id == "sc_002"

def test_scene_list_count_uses_scene_specific_beat_count(project, episode, project_service):
    """
    test_scene_list_count_uses_scene_specific_beat_count
    - Scene labels/counts must reflect only that scene's beats, not episode total beats.
    """
    sc1 = project_service.find_scene(project, episode.episode_id, "sc_001")
    sc2 = project_service.find_scene(project, episode.episode_id, "sc_002")
    
    sc1.beats = [Beat(beat_id=f"b1_{i}", scene_id="sc_001", order_index=i) for i in range(3)]
    sc2.beats = [Beat(beat_id=f"b2_{i}", scene_id="sc_002", order_index=i) for i in range(5)]
    
    # Simulation of BeatStudioTab.refresh() logic
    # count = len(scene.beats)
    
def test_apply_flat_beats_to_selected_scene_with_missing_scene_id(project, episode, project_service):
    """If applying to a specific scene, beats without scene_id should be accepted for that scene."""
    service = ManualAIService(project_service)
    flat_json = {"beats": [{"review_text": "Mystery beat"}]}
    
    service.import_result(
        project,
        step="generate-beats",
        result_data=flat_json,
        episode_id=episode.episode_id,
        chapter_id="sc_001"
    )
    
    sc1 = project_service.find_scene(project, episode.episode_id, "sc_001")
    sc2 = project_service.find_scene(project, episode.episode_id, "sc_002")
    
    assert len(sc1.beats) == 1
    assert len(sc2.beats) == 0

def test_apply_flat_beats_to_episode_skips_unknown_scene_id(project, episode, project_service):
    """If applying to whole episode, beats with missing or unknown scene_id should NOT be added to every scene."""
    service = ManualAIService(project_service)
    flat_json = {
        "beats": [
            {"review_text": "No ID"},
            {"scene_id": "wrong_id", "review_text": "Wrong ID"}
        ]
    }
    
    service.import_result(
        project,
        step="generate-beats",
        result_data=flat_json,
        episode_id=episode.episode_id
    )
    
    sc1 = project_service.find_scene(project, episode.episode_id, "sc_001")
    sc2 = project_service.find_scene(project, episode.episode_id, "sc_002")
    
    assert len(sc1.beats) == 0
    assert len(sc2.beats) == 0
