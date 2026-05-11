import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from app import cli
from app.services.project_service import ProjectService
from tests.test_production_readiness_service import (
    build_ready_project,
    duplicate_episode,
)


class CliExportProfileTests(unittest.TestCase):
    def test_cli_list_export_profiles(self) -> None:
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = cli.main(["list-export-profiles"])

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("production_markdown", output)
        self.assertIn("quality_report_package", output)

    def test_cli_export_profile(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            output_dir = Path(temp_dir) / "exports"
            project, _beat = build_ready_project()
            ProjectService().save_project(project, project_path)

            exit_code = cli.main(
                [
                    "export-profile",
                    "--project",
                    str(project_path),
                    "--episode-id",
                    "ep_001",
                    "--profile",
                    "production_markdown",
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue((output_dir / "episode_001_production.md").exists())

    def test_cli_batch_export_profile(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            output_dir = Path(temp_dir) / "exports"
            project, _beat = build_ready_project()
            duplicate_episode(project, source_episode_id="ep_001", new_episode_id="ep_002")
            ProjectService().save_project(project, project_path)

            exit_code = cli.main(
                [
                    "batch-export-profile",
                    "--project",
                    str(project_path),
                    "--episode-ids",
                    "ep_001,ep_002",
                    "--profile",
                    "batch_package",
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue((output_dir / "episode_001_production.md").exists())
            self.assertTrue((output_dir / "episode_002_production.md").exists())


if __name__ == "__main__":
    unittest.main()
