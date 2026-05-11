import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from app import cli
from app.services.project_service import ProjectService


class CliProjectTemplatesTests(unittest.TestCase):
    def test_cli_list_templates(self) -> None:
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = cli.main(["list-templates"])

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("dark_fantasy_webtoon", output)
        self.assertIn("soft_watercolor_webtoon", output)

    def test_cli_create_project_from_template(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"

            exit_code = cli.main(
                [
                    "create-project-from-template",
                    "--template",
                    "dark_fantasy_webtoon",
                    "--title",
                    "Template CLI Story",
                    "--output",
                    str(project_path),
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue(project_path.exists())
            project = ProjectService().load_project(project_path)
            self.assertEqual(project.title, "Template CLI Story")
            self.assertEqual(project.default_art_style, "dark_fantasy_webtoon")
            self.assertEqual(project.default_narration_style, "mysterious")

    def test_cli_apply_template(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            project_service = ProjectService()
            project = project_service.create_project("Basic Story")
            chapter = project_service.add_source_chapter(
                project,
                title="Chapter 1",
                chapter_number=1,
                raw_text="Keep this raw text.",
            )
            project_service.save_project(project, project_path)

            exit_code = cli.main(
                [
                    "apply-template",
                    "--project",
                    str(project_path),
                    "--template",
                    "dark_fantasy_webtoon",
                ]
            )

            self.assertEqual(exit_code, 0)
            loaded = ProjectService().load_project(project_path)
            self.assertEqual(loaded.source_chapters[0].chapter_id, chapter.chapter_id)
            self.assertEqual(loaded.source_chapters[0].raw_text, "Keep this raw text.")
            self.assertEqual(loaded.default_art_style, "dark_fantasy_webtoon")
            self.assertTrue(loaded.style_presets)


if __name__ == "__main__":
    unittest.main()
