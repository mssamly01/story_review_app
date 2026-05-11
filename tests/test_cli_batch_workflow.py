import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app import cli
from app.services.project_service import ProjectService
from tests.test_batch_workflow_service import build_project_with_chapters


class CliBatchWorkflowTests(unittest.TestCase):
    def test_cli_plan_batch_episodes(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            ProjectService().save_project(build_project_with_chapters(4), project_path)

            exit_code = cli.main(
                [
                    "plan-batch-episodes",
                    "--project",
                    str(project_path),
                    "--chapter-ids",
                    "ch_001,ch_002,ch_003,ch_004",
                    "--chapters-per-episode",
                    "2",
                    "--tone",
                    "mysterious",
                    "--density",
                    "full",
                ]
            )

            project = ProjectService().load_project(project_path)
            self.assertEqual(exit_code, 0)
            self.assertEqual(len(project.review_episodes), 2)
            self.assertEqual(
                project.review_episodes[0].source_chapter_ids,
                ["ch_001", "ch_002"],
            )
            self.assertEqual(
                project.review_episodes[1].source_chapter_ids,
                ["ch_003", "ch_004"],
            )

    def test_cli_run_batch_pipeline(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            output_dir = Path(temp_dir) / "exports"
            ProjectService().save_project(build_project_with_chapters(4), project_path)
            self.assertEqual(
                cli.main(
                    [
                        "plan-batch-episodes",
                        "--project",
                        str(project_path),
                        "--chapter-ids",
                        "ch_001,ch_002,ch_003,ch_004",
                        "--chapters-per-episode",
                        "2",
                    ]
                ),
                0,
            )

            exit_code = cli.main(
                [
                    "run-batch-pipeline",
                    "--project",
                    str(project_path),
                    "--episode-ids",
                    "ep_001,ep_002",
                    "--output-dir",
                    str(output_dir),
                    "--export-formats",
                    "markdown,json,csv,review-txt,prompts-txt",
                    "--tone",
                    "mysterious",
                    "--density",
                    "full",
                ]
            )

            project = ProjectService().load_project(project_path)
            beats = [
                beat
                for episode in project.review_episodes
                for scene in episode.scenes
                for beat in scene.beats
            ]
            self.assertEqual(exit_code, 0)
            self.assertTrue(beats)
            self.assertTrue(all(beat.review_text for beat in beats))
            self.assertTrue(all(beat.image_prompt for beat in beats))
            self.assertTrue((output_dir / "episode_001.md").exists())
            self.assertTrue((output_dir / "episode_002_prompts.txt").exists())
            self.assertIn(
                "Image prompt",
                (output_dir / "episode_001.md").read_text(encoding="utf-8"),
            )

    def test_cli_batch_workflow_no_network_required(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            output_dir = Path(temp_dir) / "exports"
            ProjectService().save_project(build_project_with_chapters(2), project_path)

            self.assertEqual(
                cli.main(
                    [
                        "plan-batch-episodes",
                        "--project",
                        str(project_path),
                        "--chapter-ids",
                        "ch_001,ch_002",
                        "--chapters-per-episode",
                        "2",
                        "--use-ai",
                        "--mock-ai",
                    ]
                ),
                0,
            )
            exit_code = cli.main(
                [
                    "run-batch-pipeline",
                    "--project",
                    str(project_path),
                    "--episode-ids",
                    "ep_001",
                    "--output-dir",
                    str(output_dir),
                    "--export-formats",
                    "markdown",
                    "--use-ai",
                    "--mock-ai",
                ]
            )

            project = ProjectService().load_project(project_path)
            self.assertEqual(exit_code, 0)
            self.assertEqual(project.review_episodes[0].title, "Mock Review Episode")
            self.assertTrue((output_dir / "episode_001.md").exists())


if __name__ == "__main__":
    unittest.main()
