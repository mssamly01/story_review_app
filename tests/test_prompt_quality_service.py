import unittest

from app.domain.character import Character
from app.domain.location import Location
from app.domain.style_preset import StylePreset
from app.services.bible_service import BibleService
from app.services.project_service import ProjectService
from app.services.prompt_quality_service import PromptQualityService


class PromptQualityServiceTests(unittest.TestCase):
    def test_high_quality_prompt_gets_a_grade(self) -> None:
        project, beat = build_quality_project()

        result = PromptQualityService().score_beat_prompt(project, beat.beat_id)

        self.assertGreaterEqual(result.score, 90)
        self.assertEqual(result.grade, "A")
        self.assertTrue(result.is_ready)

    def test_missing_prompt_gets_f_grade(self) -> None:
        project, beat = build_quality_project()
        beat.image_prompt = ""

        result = PromptQualityService().score_beat_prompt(project, beat.beat_id)

        self.assertEqual(result.grade, "F")
        self.assertFalse(result.is_ready)
        self.assertIn("missing_prompt", issue_categories(result))

    def test_missing_negative_prompt_penalized(self) -> None:
        project, beat = build_quality_project()
        beat.negative_prompt = ""

        result = PromptQualityService().score_beat_prompt(project, beat.beat_id)

        self.assertLess(result.score, 100)
        self.assertIn("weak_negative_prompt", issue_categories(result))

    def test_referenced_character_missing_from_prompt_penalized(self) -> None:
        project, beat = build_quality_project()
        beat.image_prompt = (
            "dark fantasy webtoon style, cinematic shadows, high quality illustration, "
            "dusty old hallway, wooden floor, moonlight through broken windows, "
            "discovers fresh footprints, tense expression, low angle close-up"
        )

        result = PromptQualityService().score_beat_prompt(project, beat.beat_id)

        categories = issue_categories(result)
        self.assertIn("missing_character_detail", categories)
        self.assertIn("missing_outfit", categories)

    def test_referenced_location_missing_from_prompt_penalized(self) -> None:
        project, beat = build_quality_project()
        beat.image_prompt = (
            "dark fantasy webtoon style, cinematic shadows, high quality illustration, "
            "young man with messy black hair and gray eyes, black jacket and white shirt, "
            "discovers fresh footprints, tense expression, low angle close-up"
        )

        result = PromptQualityService().score_beat_prompt(project, beat.beat_id)

        self.assertIn("missing_location_detail", issue_categories(result))

    def test_prompt_asking_for_text_logo_watermark_penalized(self) -> None:
        project, beat = build_quality_project()
        beat.image_prompt += ", add subtitles, visible text, logo, watermark, speech bubble"

        result = PromptQualityService().score_beat_prompt(project, beat.beat_id)

        categories = issue_categories(result)
        self.assertIn("asks_for_text", categories)
        self.assertIn("asks_for_logo_or_watermark", categories)
        self.assertFalse(result.is_ready)
        self.assertTrue(any(issue.severity == "error" for issue in result.issues))

    def test_missing_camera_or_emotion_penalized(self) -> None:
        project, beat = build_quality_project()
        beat.image_prompt = (
            "dark fantasy webtoon style, cinematic shadows, high quality illustration, "
            "young man with messy black hair and gray eyes, black jacket and white shirt, "
            "dusty old hallway, wooden floor, moonlight through broken windows, "
            "discovers fresh footprints"
        )

        result = PromptQualityService().score_beat_prompt(project, beat.beat_id)

        categories = issue_categories(result)
        self.assertIn("missing_camera_shot", categories)
        self.assertIn("missing_emotion", categories)

    def test_episode_report_summary(self) -> None:
        project, beat = build_quality_project()
        scene = project.review_episodes[0].scenes[0]
        project_service = ProjectService()
        weak_beat = project_service.add_beat(
            project,
            episode_id="ep_001",
            scene_id=scene.scene_id,
            beat_id="b_weak",
            order_index=2,
            characters=["lam_vu"],
            location="old_hall",
            action="opens a sealed letter",
            emotion="curious",
            shot_type="medium shot",
            visual_description="letter in his hands",
            image_prompt="short prompt",
            negative_prompt="",
        )

        report = PromptQualityService().build_episode_report(project, "ep_001")

        self.assertEqual(report["total_beats"], 2)
        self.assertEqual(report["ready_count"], 1)
        self.assertEqual(report["not_ready_count"], 1)
        self.assertIn("A", report["grade_distribution"])
        self.assertEqual(report["worst_beats"][0]["beat_id"], weak_beat.beat_id)
        self.assertTrue(report["common_issues"])

    def test_export_episode_report_markdown(self) -> None:
        project, beat = build_quality_project()

        markdown = PromptQualityService().export_episode_report_markdown(
            project,
            "ep_001",
        )

        self.assertIn("Prompt Quality Report", markdown)
        self.assertIn("Episode 1", markdown)
        self.assertIn(beat.beat_id, markdown)
        self.assertIn("Grade Distribution", markdown)

    def test_prompt_quality_does_not_modify_project(self) -> None:
        project, _beat = build_quality_project()
        before = project.to_dict()

        service = PromptQualityService()
        service.score_episode_prompts(project, "ep_001")
        service.build_episode_report(project, "ep_001")
        service.export_episode_report_markdown(project, "ep_001")

        self.assertEqual(project.to_dict(), before)


def build_quality_project():
    project_service = ProjectService()
    project = project_service.create_project(
        "Quality Story",
        default_art_style="dark_fantasy_webtoon",
    )
    chapter = project_service.add_source_chapter(
        project,
        title="Chapter 1",
        chapter_number=1,
        raw_text="Lam Vu discovers fresh footprints in the old hallway.",
    )
    BibleService().add_or_update_character(
        project,
        Character(
            character_id="lam_vu",
            name="Lam Vu",
            visual_prompt_base="young man with messy black hair and gray eyes",
            default_outfit="black jacket and white shirt",
        ),
    )
    BibleService().add_or_update_location(
        project,
        Location(
            location_id="old_hall",
            name="Old Hall",
            visual_prompt_base="dusty old hallway, wooden floor",
            mood="mysterious",
            lighting="moonlight through broken windows",
        ),
    )
    BibleService().add_or_update_style_preset(
        project,
        StylePreset(
            style_id="dark_fantasy_webtoon",
            name="Dark Fantasy Webtoon",
            positive_prompt=(
                "dark fantasy webtoon style, cinematic shadows, high quality illustration"
            ),
            negative_prompt="low quality, blurry",
        ),
    )
    episode = project_service.add_review_episode(
        project,
        title="Episode 1",
        source_chapter_ids=[chapter.chapter_id],
        episode_id="ep_001",
    )
    scene = project_service.add_scene(
        project,
        episode_id=episode.episode_id,
        title="Fresh footprints",
        summary="Lam Vu studies the hallway clue.",
        characters=["lam_vu"],
        location="old_hall",
        mood="mysterious",
    )
    beat = project_service.add_beat(
        project,
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        beat_id="b_001",
        order_index=1,
        characters=["lam_vu"],
        location="old_hall",
        action="discovers fresh footprints",
        emotion="tense",
        shot_type="low angle close-up",
        visual_description="fresh footprints on dusty floor near locked door",
        review_text="Lam Vu slows down when he sees the footprints.",
        image_prompt=(
            "dark fantasy webtoon style, cinematic shadows, high quality illustration, "
            "young man with messy black hair and gray eyes, black jacket and white shirt, "
            "dusty old hallway, wooden floor, moonlight through broken windows, "
            "mysterious atmosphere, discovers fresh footprints, tense expression, "
            "low angle close-up, fresh footprints on dusty floor near locked door, "
            "single clear visual moment"
        ),
        negative_prompt=(
            "low quality, blurry, distorted anatomy, extra fingers, "
            "inconsistent face, wrong outfit, text, watermark, logo"
        ),
    )
    return project, beat


def issue_categories(result) -> set[str]:
    return {issue.category for issue in result.issues}


if __name__ == "__main__":
    unittest.main()
