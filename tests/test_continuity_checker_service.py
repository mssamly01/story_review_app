import unittest

from app.services.continuity_checker_service import ContinuityCheckerService
from tests.test_project_validation_service import build_complete_project


class ContinuityCheckerServiceTests(unittest.TestCase):
    def test_continuity_detects_missing_character_bible(self) -> None:
        project = build_complete_project()
        project.characters.clear()

        issues = ContinuityCheckerService().check_episode(project, "ep_001")

        self.assertTrue(
            any(
                issue.category == "broken_reference" and issue.entity_type == "Character"
                for issue in issues
            )
        )

    def test_continuity_detects_missing_location_bible(self) -> None:
        project = build_complete_project()
        project.locations.clear()

        issues = ContinuityCheckerService().check_episode(project, "ep_001")

        self.assertTrue(
            any(
                issue.category == "broken_reference" and issue.entity_type == "Location"
                for issue in issues
            )
        )

    def test_continuity_detects_prompt_missing_character_visual_base(self) -> None:
        project = build_complete_project()
        beat = project.review_episodes[0].scenes[0].beats[0]
        beat.image_prompt = "cinematic webtoon style, empty corridor, detail shot"

        issues = ContinuityCheckerService().check_beat(project, beat.beat_id)

        self.assert_has_category(issues, "prompt_missing_character_detail")

    def test_continuity_detects_prompt_missing_location_visual_base(self) -> None:
        project = build_complete_project()
        beat = project.review_episodes[0].scenes[0].beats[0]
        beat.image_prompt = (
            "cinematic webtoon style, young detective in navy coat, "
            "silver flashlight, empty white room, detail shot"
        )

        issues = ContinuityCheckerService().check_beat(project, beat.beat_id)

        self.assert_has_category(issues, "prompt_missing_location_detail")

    def test_continuity_detects_forbidden_text_in_prompt(self) -> None:
        project = build_complete_project()
        beat = project.review_episodes[0].scenes[0].beats[0]
        beat.image_prompt = (
            "cinematic webtoon style, young detective in navy coat, "
            "dusty old house hallway, add subtitles, logo, watermark, "
            "text, and speech bubble"
        )

        issues = ContinuityCheckerService().check_beat(project, beat.beat_id)

        self.assert_has_category(issues, "product_direction_violation")

    def test_continuity_does_not_modify_project(self) -> None:
        project = build_complete_project()
        before = project.to_dict()

        ContinuityCheckerService().check_episode(project, "ep_001")

        self.assertEqual(project.to_dict(), before)

    def assert_has_category(self, issues, category: str) -> None:
        self.assertIn(category, {issue.category for issue in issues})


if __name__ == "__main__":
    unittest.main()
