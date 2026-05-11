import unittest

from app.domain.character import Character
from app.domain.location import Location
from app.domain.style_preset import StylePreset
from app.services.batch_workflow_service import BatchWorkflowService
from app.services.bible_service import BibleService
from app.services.continuity_checker_service import ContinuityCheckerService
from app.services.project_service import ProjectService
from app.services.project_validation_service import ProjectValidationService
from app.services.prompt_builder_service import PromptBuilderService
from tests.test_batch_workflow_service import build_project_with_chapters
from tests.test_prompt_builder_advanced_bible import build_prompt_ready_project


class PhaseFifteenBibleAndStyleTests(unittest.TestCase):
    def test_validation_detects_incomplete_bible_entries(self) -> None:
        project = ProjectService().create_project("Incomplete Bible")
        BibleService().add_or_update_character(
            project,
            Character(character_id="char_1", name="Character One"),
        )
        BibleService().add_or_update_location(
            project,
            Location(location_id="loc_1", name="Location One"),
        )
        BibleService().add_or_update_style_preset(
            project,
            StylePreset(style_id="style_1", name="Style One"),
        )

        issues = ProjectValidationService().validate_project(project)
        categories = {issue.category for issue in issues}

        self.assertIn("character_missing_visual_base", categories)
        self.assertIn("location_missing_visual_base", categories)
        self.assertTrue(
            any(
                issue.entity_type == "StylePreset"
                and issue.category == "missing_required_field"
                for issue in issues
            )
        )

    def test_continuity_detects_prompt_missing_outfit(self) -> None:
        project, beat = build_prompt_ready_project()
        beat.image_prompt = (
            "noir detective comic style, young detective with silver eyes, "
            "old archive room, tall shelves, green desk lamp"
        )
        beat.negative_prompt = "low quality, text, watermark, logo, captions"

        issues = ContinuityCheckerService().check_beat(project, beat.beat_id)

        self.assertIn("outfit_continuity", {issue.category for issue in issues})

    def test_backward_compatibility_old_minimal_character_location_style(self) -> None:
        project_service = ProjectService()
        project = project_service.create_project("Old Project")
        chapter = project_service.add_source_chapter(
            project,
            title="Chapter 1",
            chapter_number=1,
            raw_text="Lan enters the room.",
        )
        project.characters.append(
            Character.from_dict(
                {
                    "character_id": "lan",
                    "name": "Lan",
                    "appearance": "young woman",
                }
            )
        )
        project.locations.append(
            Location.from_dict(
                {
                    "location_id": "room",
                    "name": "Room",
                    "description": "small room",
                }
            )
        )
        project.style_presets.append(
            StylePreset.from_dict(
                {
                    "style_id": "minimal",
                    "name": "Minimal Style",
                }
            )
        )
        episode = project_service.add_review_episode(
            project,
            title="Episode 1",
            source_chapter_ids=[chapter.chapter_id],
        )
        scene = project_service.add_scene(
            project,
            episode_id=episode.episode_id,
            title="Room",
            characters=["lan"],
            location="room",
        )
        beat = project_service.add_beat(
            project,
            episode_id=episode.episode_id,
            scene_id=scene.scene_id,
            characters=["lan"],
            location="room",
            action="Lan looks around",
            emotion="curious",
            shot_type="medium shot",
            visual_description="Lan stands in the room.",
        )

        PromptBuilderService().build_prompt_for_beat(project, beat.beat_id)

        self.assertIn("Minimal Style", beat.image_prompt)
        self.assertIn("young woman", beat.image_prompt)
        self.assertIn("small room", beat.image_prompt)

    def test_batch_workflow_uses_advanced_style(self) -> None:
        project = build_project_with_chapters(2)
        project.default_art_style = "noir_detective_comic"
        BibleService().create_default_style_presets(project)
        service = BatchWorkflowService()
        episodes = service.plan_episodes_from_chapters(
            project,
            ["ch_001", "ch_002"],
            chapters_per_episode=2,
            tone="mysterious",
            density="balanced",
        )

        service.run_generation_for_episodes(
            project,
            [episodes[0].episode_id],
            tone="mysterious",
            density="balanced",
            style_preset_id="noir_detective_comic",
        )

        beats = [beat for scene in episodes[0].scenes for beat in scene.beats]
        self.assertTrue(beats)
        self.assertTrue(
            all("noir detective comic style" in beat.image_prompt for beat in beats)
        )


if __name__ == "__main__":
    unittest.main()
