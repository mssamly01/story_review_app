import unittest

from app.controllers.batch_workflow_controller import BatchWorkflowController
from app.infrastructure.mock_ai_gateway import MockAIGateway
from app.services.batch_workflow_service import BatchWorkflowService
from tests.test_batch_workflow_service import build_project_with_chapters


class BatchWorkflowIntegrationTests(unittest.TestCase):
    def test_batch_workflow_mock_ai_offline(self) -> None:
        project = build_project_with_chapters(2)
        service = BatchWorkflowService(ai_gateway=MockAIGateway())

        episodes = service.plan_episodes_from_chapters(
            project,
            ["ch_001", "ch_002"],
            chapters_per_episode=2,
            tone="mysterious",
            density="full",
            use_ai=True,
        )
        generated = service.run_generation_for_episodes(
            project,
            [episodes[0].episode_id],
            tone="mysterious",
            density="full",
            use_ai=True,
        )

        beats = [beat for scene in generated[0].scenes for beat in scene.beats]
        self.assertEqual(generated[0].title, "Mock Review Episode")
        self.assertTrue(beats)
        self.assertTrue(all(beat.review_text for beat in beats))
        self.assertTrue(all(beat.image_prompt for beat in beats))

    def test_batch_workflow_controller_deterministic_pipeline(self) -> None:
        project = build_project_with_chapters(3)
        controller = BatchWorkflowController()

        episodes = controller.plan_episodes_from_chapters(
            project,
            chapter_ids=["ch_001", "ch_002", "ch_003"],
            chapters_per_episode=2,
            tone="mysterious",
            density="balanced",
        )
        generated = controller.run_generation_for_episodes(
            project,
            episode_ids=[episode.episode_id for episode in episodes],
            tone="mysterious",
            density="balanced",
            validate=True,
        )

        self.assertEqual(len(generated), 2)
        self.assertEqual(episodes[-1].source_chapter_ids, ["ch_003"])
        self.assertTrue(controller.last_validation_issues)
        self.assertTrue(all(scene.beats for episode in generated for scene in episode.scenes))


if __name__ == "__main__":
    unittest.main()
