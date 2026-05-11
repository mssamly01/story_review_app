import json
import unittest

from app.domain.character import Character
from app.domain.location import Location
from app.domain.style_preset import StylePreset
from app.services.bible_service import BibleService
from app.services.quality.readiness import ProductionReadinessService
from app.services.project_service import ProjectService


class ProductionReadinessServiceTests(unittest.TestCase):
    def test_ready_episode_gets_ready_status(self) -> None:
        project, _beat = build_ready_project()

        report = readiness_service().build_episode_report(project, "ep_001")

        self.assertEqual(report.status, "ready")
        self.assertGreaterEqual(report.overall_score, 80)
        self.assertEqual(report.validation_error_count, 0)
        self.assertTrue(report.export_readiness["is_ready"])

    def test_missing_review_text_blocks_report(self) -> None:
        project, beat = build_ready_project()
        beat.review_text = ""

        report = readiness_service().build_episode_report(project, "ep_001")

        self.assertEqual(report.status, "blocked")
        self.assertTrue(
            any("review text" in reason.lower() for reason in report.blocked_reasons)
        )
        self.assertIn("Run rewrite-review", " ".join(report.top_recommendations))

    def test_missing_image_prompt_blocks_report(self) -> None:
        project, beat = build_ready_project()
        beat.image_prompt = ""

        report = readiness_service().build_episode_report(project, "ep_001")

        self.assertEqual(report.status, "blocked")
        self.assertTrue(
            any("image prompt" in reason.lower() for reason in report.blocked_reasons)
        )
        self.assertIn("Run build-prompts", " ".join(report.top_recommendations))

    def test_low_review_quality_needs_review(self) -> None:
        project, beat = build_ready_project()
        beat.review_text = "Lam Vu sees clues."

        report = readiness_service().build_episode_report(project, "ep_001")

        self.assertIn(report.status, {"needs_review", "blocked"})
        self.assertIn("review narration", " ".join(report.top_recommendations))

    def test_low_prompt_quality_needs_review(self) -> None:
        project, beat = build_ready_project()
        beat.image_prompt = "dark fantasy webtoon style, young man looks tense"

        report = readiness_service().build_episode_report(project, "ep_001")

        self.assertIn(report.status, {"needs_review", "blocked"})
        self.assertIn("PromptQualityService", " ".join(report.top_recommendations))

    def test_validation_error_blocks_report(self) -> None:
        project, _beat = build_ready_project()
        project.review_episodes[0].source_chapter_ids.append("missing_chapter")

        report = readiness_service().build_episode_report(project, "ep_001")

        self.assertEqual(report.status, "blocked")
        self.assertGreater(report.validation_error_count, 0)
        self.assertTrue(report.blocked_reasons)

    def test_continuity_issue_appears_in_report(self) -> None:
        project, beat = build_ready_project()
        beat.image_prompt = beat.image_prompt.replace(
            "black jacket and white shirt, ",
            "",
        )

        report = readiness_service().build_episode_report(project, "ep_001")

        self.assertGreater(report.continuity_issue_count, 0)
        self.assertIn(
            "bible and prompt consistency",
            " ".join(report.top_recommendations),
        )

    def test_overall_score_combines_review_prompt_and_issues(self) -> None:
        ready_project, _ready_beat = build_ready_project()
        weak_project, weak_beat = build_ready_project()
        weak_beat.review_text = "Lam Vu sees clues."
        weak_beat.image_prompt = "dark fantasy webtoon style, tense hallway"

        service = readiness_service()
        ready_report = service.build_episode_report(ready_project, "ep_001")
        weak_report = service.build_episode_report(weak_project, "ep_001")

        self.assertLess(weak_report.overall_score, ready_report.overall_score)

    def test_episode_report_markdown_contains_summary(self) -> None:
        project, _beat = build_ready_project()

        markdown = readiness_service().export_episode_report_markdown(
            project,
            "ep_001",
        )

        self.assertIn("Production Readiness Report", markdown)
        self.assertIn("Ready Story", markdown)
        self.assertIn("Episode 1", markdown)
        self.assertIn("Status", markdown)
        self.assertIn("Overall score", markdown)
        self.assertIn("Top Recommendations", markdown)
        self.assertIn("Validation", markdown)

    def test_episode_report_json_serializable(self) -> None:
        project, _beat = build_ready_project()

        data = readiness_service().export_episode_report_json(project, "ep_001")

        json.dumps(data)
        self.assertIn("status", data)
        self.assertIn("overall_score", data)
        self.assertIn("export_readiness", data)

    def test_readiness_report_does_not_modify_project(self) -> None:
        project, _beat = build_ready_project()
        before = project.to_dict()
        service = readiness_service()

        service.build_episode_report(project, "ep_001")
        service.export_episode_report_markdown(project, "ep_001")
        service.export_episode_report_json(project, "ep_001")

        self.assertEqual(project.to_dict(), before)

    def test_batch_readiness_report(self) -> None:
        project, _beat = build_ready_project()
        duplicate_episode(project, source_episode_id="ep_001", new_episode_id="ep_002")

        batch = readiness_service().build_batch_report(project, ["ep_001", "ep_002"])

        self.assertEqual(batch["episode_count"], 2)
        self.assertEqual(batch["ready_count"], 2)
        self.assertIn("reports", batch)


def build_ready_project():
    project_service = ProjectService()
    project = project_service.create_project(
        "Ready Story",
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
        scene_id="sc_001",
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
        review_text=(
            "Inside the old hall, Lam Vu moves through the mysterious silence and "
            "discovers fresh footprints pressed into the dust. The tense detail "
            "makes him slow down, because someone has crossed this hallway long "
            "after the house was supposed to be abandoned."
        ),
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
        continuity_tags=["lam_vu", "old_hall", "fresh_footprints"],
    )
    return project, beat


def duplicate_episode(project, *, source_episode_id: str, new_episode_id: str) -> None:
    source = next(
        episode for episode in project.review_episodes if episode.episode_id == source_episode_id
    )
    data = source.to_dict()
    data["episode_id"] = new_episode_id
    data["title"] = "Episode 2"
    for scene in data["scenes"]:
        scene["episode_id"] = new_episode_id
        scene["scene_id"] = scene["scene_id"].replace("001", "002")
        for beat in scene["beats"]:
            beat["scene_id"] = scene["scene_id"]
            beat["beat_id"] = beat["beat_id"].replace("001", "002")
    from app.domain.episode import ReviewEpisode

    project.review_episodes.append(ReviewEpisode.from_dict(data))


def readiness_service() -> ProductionReadinessService:
    return ProductionReadinessService(
        generated_at_factory=lambda: "2026-01-01T00:00:00+00:00",
    )


if __name__ == "__main__":
    unittest.main()
