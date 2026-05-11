from types import SimpleNamespace
import unittest

from app.services.project_service import ProjectService
from app.services.quality.validation import ProjectValidationService


class ProjectValidationServiceTests(unittest.TestCase):
    def test_validation_passes_for_valid_project(self) -> None:
        project = build_complete_project()

        issues = ProjectValidationService().validate_project(project)

        self.assertFalse(ProjectValidationService().has_errors(issues))

    def test_validation_detects_episode_without_scenes(self) -> None:
        project_service = ProjectService()
        project = project_service.create_project("Demo Story")
        chapter = project_service.add_source_chapter(
            project,
            title="Chapter 1",
            chapter_number=1,
            raw_text="Lan returns home.",
        )
        episode = project_service.add_review_episode(
            project,
            title="Episode 1",
            source_chapter_ids=[chapter.chapter_id],
        )

        issues = ProjectValidationService().validate_project(project)

        self.assert_has_category(issues, "episode_without_scenes")
        self.assertEqual(issues[0].episode_id, episode.episode_id)

    def test_validation_detects_scene_without_beats(self) -> None:
        project = build_complete_project()
        project.review_episodes[0].scenes[0].beats.clear()

        issues = ProjectValidationService().validate_project(project)

        self.assert_has_category(issues, "scene_without_beats")

    def test_validation_detects_broken_scene_reference(self) -> None:
        project_service = ProjectService()
        project = project_service.create_project("Demo Story")
        chapter = project_service.add_source_chapter(
            project,
            title="Chapter 1",
            chapter_number=1,
            raw_text="Lan returns home.",
        )
        project.review_episodes.append(
            SimpleNamespace(
                episode_id="ep_bad",
                title="Episode Bad",
                source_chapter_ids=[chapter.chapter_id],
                tone="mysterious",
                density="full",
                scene_ids=["sc_missing"],
                scenes=[],
            )
        )

        issues = ProjectValidationService().validate_project(project)

        self.assertTrue(
            any(
                issue.category == "broken_reference"
                and issue.scene_id == "sc_missing"
                for issue in issues
            )
        )

    def test_validation_detects_broken_beat_reference(self) -> None:
        project_service = ProjectService()
        project = project_service.create_project("Demo Story")
        chapter = project_service.add_source_chapter(
            project,
            title="Chapter 1",
            chapter_number=1,
            raw_text="Lan returns home.",
        )
        project.review_episodes.append(
            SimpleNamespace(
                episode_id="ep_bad",
                title="Episode Bad",
                source_chapter_ids=[chapter.chapter_id],
                tone="mysterious",
                density="full",
                scene_ids=["sc_bad"],
                scenes=[
                    SimpleNamespace(
                        scene_id="sc_bad",
                        episode_id="ep_bad",
                        title="Scene Bad",
                        summary="A damaged serialized scene.",
                        characters=[],
                        location="",
                        mood="",
                        beat_ids=["b_missing"],
                        beats=[],
                    )
                ],
            )
        )

        issues = ProjectValidationService().validate_project(project)

        self.assertTrue(
            any(
                issue.category == "broken_reference"
                and issue.beat_id == "b_missing"
                for issue in issues
            )
        )

    def test_validation_detects_duplicate_ids(self) -> None:
        project_service = ProjectService()
        project = project_service.create_project("Demo Story")
        project_service.add_source_chapter(
            project,
            chapter_id="ch_dup",
            title="Chapter 1",
            chapter_number=1,
            raw_text="First text.",
        )
        project_service.add_source_chapter(
            project,
            chapter_id="ch_dup",
            title="Chapter 2",
            chapter_number=2,
            raw_text="Second text.",
        )

        issues = ProjectValidationService().validate_project(project)

        self.assert_has_category(issues, "duplicate_id")

    def test_validation_detects_empty_review_text(self) -> None:
        project = build_complete_project()
        project.review_episodes[0].scenes[0].beats[0].review_text = ""

        issues = ProjectValidationService().validate_project(project)

        self.assert_has_category(issues, "empty_review_text")

    def test_validation_detects_empty_image_prompt(self) -> None:
        project = build_complete_project()
        project.review_episodes[0].scenes[0].beats[0].image_prompt = ""

        issues = ProjectValidationService().validate_project(project)

        self.assert_has_category(issues, "empty_image_prompt")

    def test_validation_does_not_modify_project(self) -> None:
        project = build_complete_project()
        before = project.to_dict()

        ProjectValidationService().validate_project(project)

        self.assertEqual(project.to_dict(), before)

    def assert_has_category(self, issues, category: str) -> None:
        self.assertIn(category, {issue.category for issue in issues})


def build_complete_project():
    project_service = ProjectService()
    project = project_service.create_project("Demo Story")
    chapter = project_service.add_source_chapter(
        project,
        title="Chapter 1",
        chapter_number=1,
        raw_text="Lan enters the old hallway and finds a clue.",
    )
    project_service.add_character(
        project,
        character_id="char_lan",
        name="Lan",
        visual_prompt_base="young detective, navy coat, silver flashlight",
    )
    project_service.add_location(
        project,
        location_id="old_hall",
        name="Old Hall",
        visual_prompt_base="dusty old house hallway, wooden floor, moonlit windows",
    )
    project_service.add_style_preset(
        project,
        style_id="webtoon",
        name="Webtoon",
        positive_prompt="cinematic webtoon style, high quality illustration",
        negative_prompt="low quality, blurry",
    )
    episode = project_service.add_review_episode(
        project,
        title="Episode 1",
        source_chapter_ids=[chapter.chapter_id],
    )
    scene = project_service.add_scene(
        project,
        episode_id=episode.episode_id,
        title="Old hallway",
        summary="Lan studies the hallway clue.",
        characters=["char_lan"],
        location="old_hall",
        mood="tense",
    )
    project_service.add_beat(
        project,
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        beat_id="b_001",
        order_index=1,
        story_function="discovery",
        characters=["char_lan"],
        location="old_hall",
        action="Lan finds a silver mark on the floor",
        emotion="curious",
        shot_type="detail shot",
        review_text="Lan cham lai khi thay dau vet sang len tren san go.",
        visual_description="Lan kneels beside a silver mark on dusty wood.",
        image_prompt=(
            "cinematic webtoon style, young detective in navy coat, "
            "silver flashlight, dusty old house hallway, wooden floor, "
            "moonlit windows, detail shot"
        ),
        negative_prompt="low quality, blurry",
        continuity_tags=["char_lan", "old_hall", "silver_mark"],
    )
    return project


if __name__ == "__main__":
    unittest.main()
