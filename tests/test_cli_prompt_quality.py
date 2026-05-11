import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from app import cli
from app.services.project_service import ProjectService
from tests.test_prompt_quality_service import build_quality_project


class CliPromptQualityTests(unittest.TestCase):
    def test_cli_score_prompts_text(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            project, _beat = build_quality_project()
            ProjectService().save_project(project, project_path)
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = cli.main(
                    [
                        "score-prompts",
                        "--project",
                        str(project_path),
                        "--episode-id",
                        "ep_001",
                    ]
                )

            self.assertEqual(exit_code, 0)
            output = stdout.getvalue()
            self.assertIn("Average score", output)
            self.assertIn("Grade distribution", output)

    def test_cli_score_prompts_markdown_output_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            output_path = Path(temp_dir) / "prompt_report.md"
            project, _beat = build_quality_project()
            ProjectService().save_project(project, project_path)

            exit_code = cli.main(
                [
                    "score-prompts",
                    "--project",
                    str(project_path),
                    "--episode-id",
                    "ep_001",
                    "--format",
                    "markdown",
                    "--output",
                    str(output_path),
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            markdown = output_path.read_text(encoding="utf-8")
            self.assertIn("Prompt Quality Report", markdown)
            self.assertIn("Episode 1", markdown)


if __name__ == "__main__":
    unittest.main()
