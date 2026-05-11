from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.services.batch_workflow_service import BatchWorkflowService
from app.services.project_service import ProjectService


class BatchWorkflowServiceTests(unittest.TestCase):
    def test_plan_episodes_from_multiple_chapters(self) -> None:
        project = build_project_with_chapters(4)

        episodes = BatchWorkflowService().plan_episodes_from_chapters(
            project,
            ["ch_001", "ch_002", "ch_003", "ch_004"],
            chapters_per_episode=2,
            tone="mysterious",
            density="full",
        )

        self.assertEqual(len(episodes), 2)
        self.assertEqual(episodes[0].source_chapter_ids, ["ch_001", "ch_002"])
        self.assertEqual(episodes[1].source_chapter_ids, ["ch_003", "ch_004"])
        self.assertEqual([episode.tone for episode in episodes], ["mysterious"] * 2)
        self.assertEqual([episode.density for episode in episodes], ["full"] * 2)

    def test_plan_episodes_handles_remainder_chapter(self) -> None:
        project = build_project_with_chapters(5)

        episodes = BatchWorkflowService().plan_episodes_from_chapters(
            project,
            ["ch_001", "ch_002", "ch_003", "ch_004", "ch_005"],
            chapters_per_episode=2,
            tone="mysterious",
            density="balanced",
        )

        self.assertEqual(len(episodes), 3)
        self.assertEqual(episodes[-1].source_chapter_ids, ["ch_005"])

    def test_plan_episodes_is_idempotent_for_same_grouping(self) -> None:
        project = build_project_with_chapters(4)
        service = BatchWorkflowService()

        first = service.plan_episodes_from_chapters(
            project,
            ["ch_001", "ch_002", "ch_003", "ch_004"],
            chapters_per_episode=2,
            tone="mysterious",
            density="full",
        )
        second = service.plan_episodes_from_chapters(
            project,
            ["ch_001", "ch_002", "ch_003", "ch_004"],
            chapters_per_episode=2,
            tone="mysterious",
            density="full",
        )

        self.assertEqual(len(project.review_episodes), 2)
        self.assertEqual(
            [episode.episode_id for episode in first],
            [episode.episode_id for episode in second],
        )

    def test_batch_generation_for_multiple_episodes(self) -> None:
        project, episodes = plan_sample_batch()

        generated = BatchWorkflowService().run_generation_for_episodes(
            project,
            [episode.episode_id for episode in episodes],
            tone="mysterious",
            density="full",
        )

        self.assertEqual(len(generated), 2)
        for episode in generated:
            beats = [beat for scene in episode.scenes for beat in scene.beats]
            self.assertTrue(episode.scenes)
            self.assertTrue(beats)
            self.assertTrue(all(beat.review_text for beat in beats))
            self.assertTrue(all(beat.image_prompt for beat in beats))
            self.assertTrue(all(beat.negative_prompt for beat in beats))

    def test_batch_generation_preserves_source_raw_text(self) -> None:
        project, episodes = plan_sample_batch()
        raw_text_by_id = {
            chapter.chapter_id: chapter.raw_text
            for chapter in project.source_chapters
        }

        BatchWorkflowService().run_generation_for_episodes(
            project,
            [episode.episode_id for episode in episodes],
            tone="mysterious",
            density="full",
        )

        self.assertEqual(
            {
                chapter.chapter_id: chapter.raw_text
                for chapter in project.source_chapters
            },
            raw_text_by_id,
        )

    def test_batch_generation_is_idempotent(self) -> None:
        project, episodes = plan_sample_batch()
        service = BatchWorkflowService()
        episode_ids = [episode.episode_id for episode in episodes]

        service.run_generation_for_episodes(project, episode_ids, density="full")
        first_signature = beat_signature(project)
        service.run_generation_for_episodes(project, episode_ids, density="full")
        second_signature = beat_signature(project)

        self.assertEqual(second_signature, first_signature)

    def test_batch_export_multiple_formats(self) -> None:
        project, episodes = generated_sample_batch()
        episode_ids = [episode.episode_id for episode in episodes]
        with TemporaryDirectory() as temp_dir:
            paths = BatchWorkflowService().export_episodes(
                project,
                episode_ids,
                temp_dir,
                ["markdown", "json", "csv", "review-txt", "prompts-txt"],
            )

            self.assertEqual(len(paths), 10)
            self.assertTrue(all(path.exists() for path in paths))
            self.assertTrue((Path(temp_dir) / "episode_001.md").exists())
            self.assertTrue((Path(temp_dir) / "episode_001.json").exists())
            self.assertTrue((Path(temp_dir) / "episode_001.csv").exists())
            self.assertTrue((Path(temp_dir) / "episode_001_review.txt").exists())
            self.assertTrue((Path(temp_dir) / "episode_001_prompts.txt").exists())
            self.assertIn(
                "Image prompt",
                (Path(temp_dir) / "episode_001.md").read_text(encoding="utf-8"),
            )

    def test_batch_export_does_not_modify_project(self) -> None:
        project, episodes = generated_sample_batch()
        before = project.to_dict()
        with TemporaryDirectory() as temp_dir:
            BatchWorkflowService().export_episodes(
                project,
                [episode.episode_id for episode in episodes],
                temp_dir,
                ["markdown", "json", "csv"],
            )

        self.assertEqual(project.to_dict(), before)

    def test_batch_validation_integration(self) -> None:
        project, episodes = plan_sample_batch()
        service = BatchWorkflowService()

        service.run_generation_for_episodes(
            project,
            [episodes[0].episode_id],
            validate=True,
            fail_on_validation_error=False,
        )

        self.assertIn(episodes[0].episode_id, service.last_validation_issues)
        self.assertFalse(
            any(
                issue.severity == "error"
                for issue in service.last_validation_issues[episodes[0].episode_id]
            )
        )

        episodes[1].source_chapter_ids.append("ch_missing")
        with self.assertRaisesRegex(ValueError, "Batch validation failed"):
            service.run_generation_for_episodes(
                project,
                [episodes[1].episode_id],
                validate=True,
                fail_on_validation_error=True,
            )


def build_project_with_chapters(count: int):
    project_service = ProjectService()
    project = project_service.create_project("Batch Story")
    for index in range(1, count + 1):
        project_service.add_source_chapter(
            project,
            title=f"Chapter {index}",
            chapter_number=index,
            raw_text=(
                f"chapter {index} opens with a quiet clue on the floor.\n\n"
                f"chapter {index} continues with a careful search."
            ),
        )
    return project


def plan_sample_batch():
    project = build_project_with_chapters(4)
    episodes = BatchWorkflowService().plan_episodes_from_chapters(
        project,
        ["ch_001", "ch_002", "ch_003", "ch_004"],
        chapters_per_episode=2,
        tone="mysterious",
        density="full",
    )
    return project, episodes


def generated_sample_batch():
    project, episodes = plan_sample_batch()
    BatchWorkflowService().run_generation_for_episodes(
        project,
        [episode.episode_id for episode in episodes],
        tone="mysterious",
        density="full",
    )
    return project, episodes


def beat_signature(project) -> list[tuple[str, str, tuple[str, ...]]]:
    return [
        (
            episode.episode_id,
            scene.scene_id,
            tuple(beat.beat_id for beat in scene.ordered_beats()),
        )
        for episode in project.review_episodes
        for scene in episode.scenes
    ]


if __name__ == "__main__":
    unittest.main()
