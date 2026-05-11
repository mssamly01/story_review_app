import unittest

from app.services.batch_workflow_service import BatchWorkflowService
from app.services.bible_service import BibleService
from app.services.quality.prompt import PromptQualityService
from tests.test_batch_workflow_service import build_project_with_chapters


class PhaseSixteenPromptQualityTests(unittest.TestCase):
    def test_batch_workflow_can_be_scored_after_generation(self) -> None:
        project = build_project_with_chapters(2)
        BibleService().create_default_style_presets(project)
        project.default_art_style = "dark_fantasy_webtoon"
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
            style_preset_id="dark_fantasy_webtoon",
        )

        results = PromptQualityService().score_episode_prompts(
            project,
            episodes[0].episode_id,
        )

        beat_count = sum(len(scene.beats) for scene in episodes[0].scenes)
        self.assertEqual(len(results), beat_count)
        self.assertTrue(all(0 <= result.score <= 100 for result in results))
        self.assertTrue(all(result.grade in {"A", "B", "C", "D", "F"} for result in results))


if __name__ == "__main__":
    unittest.main()
