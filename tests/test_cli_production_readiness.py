import io
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app import cli
from app.services.project_service import ProjectService
from tests.test_production_readiness_service import build_ready_project


class CliProductionReadinessTests(unittest.TestCase):
    def test_cli_readiness_report_text(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            project, _beat = build_ready_project()
            ProjectService().save_project(project, project_path)
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = cli.main(
                    [
                        "readiness-report",
                        "--project",
                        str(project_path),
                        "--episode-id",
                        "ep_001",
                    ]
                )

            self.assertEqual(exit_code, 0)
            output = stdout.getvalue()
            self.assertIn("Status", output)
            self.assertIn("Overall score", output)

    def test_cli_readiness_report_markdown_output_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            output_path = Path(temp_dir) / "readiness.md"
            project, _beat = build_ready_project()
            ProjectService().save_project(project, project_path)

            exit_code = cli.main(
                [
                    "readiness-report",
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
            self.assertIn(
                "Production Readiness Report",
                output_path.read_text(encoding="utf-8"),
            )

    def test_cli_readiness_report_fail_if_blocked(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            project, beat = build_ready_project()
            beat.review_text = ""
            ProjectService().save_project(project, project_path)

            exit_code = cli.main(
                [
                    "readiness-report",
                    "--project",
                    str(project_path),
                    "--episode-id",
                    "ep_001",
                    "--fail-if-blocked",
                ]
            )

            self.assertNotEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
