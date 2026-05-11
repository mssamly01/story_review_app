import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app import cli
from app.services.project_service import ProjectService


class CliWorkflowTests(unittest.TestCase):
    def test_cli_full_deterministic_workflow(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            chapter_path = Path(temp_dir) / "chapter.txt"
            export_path = Path(temp_dir) / "episode.md"
            chapter_path.write_text(
                "Lan returns to the old house.\n\nShe finds a clue on the floor.",
                encoding="utf-8",
            )

            self.assertEqual(
                cli.main(
                    [
                        "create-project",
                        "--title",
                        "Demo Story",
                        "--output",
                        str(project_path),
                    ]
                ),
                0,
            )
            self.assertEqual(
                cli.main(
                    [
                        "add-chapter",
                        "--project",
                        str(project_path),
                        "--title",
                        "Chapter 1",
                        "--chapter-number",
                        "1",
                        "--text-file",
                        str(chapter_path),
                    ]
                ),
                0,
            )
            self.assertEqual(
                cli.main(
                    [
                        "plan-episode",
                        "--project",
                        str(project_path),
                        "--chapter-id",
                        "ch_001",
                        "--episode-title",
                        "Episode 1",
                        "--tone",
                        "mysterious",
                        "--density",
                        "full",
                    ]
                ),
                0,
            )
            self.assertEqual(
                cli.main(
                    [
                        "generate-beats",
                        "--project",
                        str(project_path),
                        "--episode-id",
                        "ep_001",
                        "--density",
                        "full",
                    ]
                ),
                0,
            )
            self.assertEqual(
                cli.main(
                    [
                        "rewrite-review",
                        "--project",
                        str(project_path),
                        "--episode-id",
                        "ep_001",
                        "--tone",
                        "mysterious",
                        "--density",
                        "full",
                    ]
                ),
                0,
            )
            self.assertEqual(
                cli.main(
                    [
                        "build-prompts",
                        "--project",
                        str(project_path),
                        "--episode-id",
                        "ep_001",
                    ]
                ),
                0,
            )
            self.assertEqual(
                cli.main(
                    [
                        "export",
                        "--project",
                        str(project_path),
                        "--episode-id",
                        "ep_001",
                        "--format",
                        "markdown",
                        "--output",
                        str(export_path),
                    ]
                ),
                0,
            )

            project = ProjectService().load_project(project_path)
            episode = project.review_episodes[0]
            beats = [beat for scene in episode.scenes for beat in scene.beats]
            self.assertTrue(episode.scenes)
            self.assertTrue(beats)
            self.assertTrue(all(beat.review_text for beat in beats))
            self.assertTrue(all(beat.image_prompt for beat in beats))
            self.assertTrue(export_path.exists())

    def test_cli_mock_ai_workflow_offline(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            chapter_path = Path(temp_dir) / "chapter.txt"
            export_path = Path(temp_dir) / "episode.md"
            chapter_path.write_text(
                "Lan returns to the old house and finds a clue.",
                encoding="utf-8",
            )
            cli.main(
                [
                    "create-project",
                    "--title",
                    "Demo Story",
                    "--output",
                    str(project_path),
                ]
            )
            cli.main(
                [
                    "add-chapter",
                    "--project",
                    str(project_path),
                    "--title",
                    "Chapter 1",
                    "--chapter-number",
                    "1",
                    "--text-file",
                    str(chapter_path),
                ]
            )

            exit_code = cli.main(
                [
                    "run-pipeline",
                    "--project",
                    str(project_path),
                    "--chapter-id",
                    "ch_001",
                    "--episode-title",
                    "Episode 1",
                    "--output",
                    str(export_path),
                    "--use-ai",
                    "--mock-ai",
                ]
            )

            self.assertEqual(exit_code, 0)
            project = ProjectService().load_project(project_path)
            episode = project.review_episodes[0]
            beats = [beat for scene in episode.scenes for beat in scene.beats]
            self.assertEqual(episode.title, "Mock Review Episode")
            self.assertTrue(beats)
            self.assertIn("Mock Review Episode", export_path.read_text(encoding="utf-8"))
            self.assertTrue(all(beat.review_text for beat in beats))
            self.assertTrue(all(beat.image_prompt for beat in beats))

    def test_cli_export_does_not_modify_project(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            output_path = Path(temp_dir) / "episode.csv"
            episode_id = self._write_export_ready_project(project_path)
            before = json.loads(project_path.read_text(encoding="utf-8"))

            exit_code = cli.main(
                [
                    "export",
                    "--project",
                    str(project_path),
                    "--episode-id",
                    episode_id,
                    "--format",
                    "csv",
                    "--output",
                    str(output_path),
                ]
            )

            after = json.loads(project_path.read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 0)
            self.assertEqual(after, before)
            self.assertTrue(output_path.exists())

    def test_cli_unsupported_export_format_returns_error(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            output_path = Path(temp_dir) / "episode.out"
            episode_id = self._write_export_ready_project(project_path)

            exit_code = cli.main(
                [
                    "export",
                    "--project",
                    str(project_path),
                    "--episode-id",
                    episode_id,
                    "--format",
                    "unsupported",
                    "--output",
                    str(output_path),
                ]
            )

            self.assertNotEqual(exit_code, 0)
            self.assertFalse(output_path.exists())

    def _write_export_ready_project(self, project_path: Path) -> str:
        project_service = ProjectService()
        project = project_service.create_project("Demo Story")
        chapter = project_service.add_source_chapter(
            project,
            title="Chapter 1",
            chapter_number=1,
            raw_text="Lan returns to the old house.",
        )
        episode = project_service.add_review_episode(
            project,
            title="Episode 1",
            source_chapter_ids=[chapter.chapter_id],
        )
        scene = project_service.add_scene(
            project,
            episode_id=episode.episode_id,
            title="Scene 1",
            summary="Lan finds a clue.",
        )
        project_service.add_beat(
            project,
            episode_id=episode.episode_id,
            scene_id=scene.scene_id,
            beat_id="b_001",
            order_index=1,
            review_text="Lan notices the clue.",
            image_prompt="webtoon style, clue on dusty floor",
            negative_prompt="low quality, text, watermark, logo",
        )
        project_service.save_project(project, project_path)
        return episode.episode_id


if __name__ == "__main__":
    unittest.main()
