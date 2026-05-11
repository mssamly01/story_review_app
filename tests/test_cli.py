import io
import os
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app import cli
from app.services.project_service import ProjectService


class CliTests(unittest.TestCase):
    def test_cli_create_project(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"

            exit_code = cli.main(
                [
                    "create-project",
                    "--title",
                    "Demo Story",
                    "--output",
                    str(project_path),
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue(project_path.exists())
            project = ProjectService().load_project(project_path)
            self.assertEqual(project.title, "Demo Story")

    def test_cli_add_chapter_preserves_raw_text(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            text_path = Path(temp_dir) / "chapter1.txt"
            raw_text = "Line one.\n\nLine two, with punctuation."
            text_path.write_text(raw_text, encoding="utf-8")
            cli.main(
                [
                    "create-project",
                    "--title",
                    "Demo Story",
                    "--output",
                    str(project_path),
                ]
            )

            exit_code = cli.main(
                [
                    "add-chapter",
                    "--project",
                    str(project_path),
                    "--title",
                    "Chapter 1",
                    "--chapter-number",
                    "1",
                    "--text-file",
                    str(text_path),
                ]
            )

            self.assertEqual(exit_code, 0)
            project = ProjectService().load_project(project_path)
            self.assertEqual(project.source_chapters[0].raw_text, raw_text)

    def test_cli_export_markdown(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            output_path = Path(temp_dir) / "episode.md"
            sample = self._write_project_with_episode(project_path)

            exit_code = cli.main(
                [
                    "export",
                    "--project",
                    str(project_path),
                    "--episode-id",
                    sample["episode_id"],
                    "--format",
                    "markdown",
                    "--output",
                    str(output_path),
                ]
            )

            self.assertEqual(exit_code, 0)
            markdown = output_path.read_text(encoding="utf-8")
            self.assertIn("Episode 1", markdown)
            self.assertIn("Lan notices the clue.", markdown)
            self.assertIn("webtoon style, clue on dusty floor", markdown)

    def test_cli_invalid_command_or_missing_file_has_clear_error(self) -> None:
        with TemporaryDirectory() as temp_dir:
            missing_project = Path(temp_dir) / "missing.json"
            output_path = Path(temp_dir) / "episode.md"
            stderr = io.StringIO()

            with redirect_stderr(stderr):
                exit_code = cli.main(
                    [
                        "export",
                        "--project",
                        str(missing_project),
                        "--episode-id",
                        "ep_001",
                        "--format",
                        "markdown",
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertNotEqual(exit_code, 0)
            self.assertIn("Project file not found", stderr.getvalue())

    def test_cli_rejects_ambiguous_use_ai(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            sample = self._write_project_with_episode(project_path)
            stderr = io.StringIO()

            with redirect_stderr(stderr):
                exit_code = cli.main(
                    [
                        "parse-story",
                        "--project",
                        str(project_path),
                        "--chapter-id",
                        sample["chapter_id"],
                        "--use-ai",
                    ]
                )

            self.assertNotEqual(exit_code, 0)
            self.assertIn("requires either --mock-ai or --real-ai", stderr.getvalue())

    def test_cli_real_ai_mode_does_not_run_without_configuration(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            sample = self._write_project_with_episode(project_path)
            stderr = io.StringIO()

            with patch.dict(os.environ, {}, clear=True):
                with redirect_stderr(stderr):
                    exit_code = cli.main(
                        [
                            "parse-story",
                            "--project",
                            str(project_path),
                            "--chapter-id",
                            sample["chapter_id"],
                            "--use-ai",
                            "--real-ai",
                        ]
                    )

            self.assertNotEqual(exit_code, 0)
            self.assertIn("Real AI mode requires", stderr.getvalue())

    def _write_project_with_episode(self, project_path: Path) -> dict[str, str]:
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
            summary="Lan enters the hallway.",
            location="old_house",
            mood="mysterious",
        )
        project_service.add_beat(
            project,
            episode_id=episode.episode_id,
            scene_id=scene.scene_id,
            beat_id="b_001",
            order_index=1,
            story_function="discovery",
            action="finds a clue",
            emotion="curious",
            shot_type="detail shot",
            review_text="Lan notices the clue.",
            visual_description="a clue on a dusty floor",
            image_prompt="webtoon style, clue on dusty floor",
            negative_prompt="low quality, text, watermark, logo",
        )
        project_service.save_project(project, project_path)
        return {"chapter_id": chapter.chapter_id, "episode_id": episode.episode_id}


if __name__ == "__main__":
    unittest.main()
