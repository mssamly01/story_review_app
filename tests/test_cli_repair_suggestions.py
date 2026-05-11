import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app import cli
from app.services.project_service import ProjectService
from tests.test_production_readiness_service import build_ready_project


class CliRepairSuggestionTests(unittest.TestCase):
    def test_apply_repairs_can_save_via_cli_only_when_save_passed(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            project, beat = build_ready_project()
            beat.image_prompt = ""
            beat.negative_prompt = ""
            ProjectService().save_project(project, project_path)

            exit_code = cli.main(
                [
                    "apply-repairs",
                    "--project",
                    str(project_path),
                    "--episode-id",
                    "ep_001",
                    "--low-risk-only",
                ]
            )

            self.assertEqual(exit_code, 0)
            reloaded = ProjectService().load_project(project_path)
            reloaded_beat = reloaded.review_episodes[0].scenes[0].beats[0]
            self.assertEqual(reloaded_beat.image_prompt, "")

            exit_code = cli.main(
                [
                    "apply-repairs",
                    "--project",
                    str(project_path),
                    "--episode-id",
                    "ep_001",
                    "--low-risk-only",
                    "--save",
                ]
            )

            self.assertEqual(exit_code, 0)
            reloaded = ProjectService().load_project(project_path)
            reloaded_beat = reloaded.review_episodes[0].scenes[0].beats[0]
            self.assertTrue(reloaded_beat.image_prompt)
            self.assertTrue(reloaded_beat.negative_prompt)

    def test_cli_suggest_repairs_text(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            project, beat = build_ready_project()
            beat.review_text = ""
            ProjectService().save_project(project, project_path)
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = cli.main(
                    [
                        "suggest-repairs",
                        "--project",
                        str(project_path),
                        "--episode-id",
                        "ep_001",
                    ]
                )

            self.assertEqual(exit_code, 0)
            output = stdout.getvalue()
            self.assertIn("rewrite_review_text", output)
            self.assertIn("Repair suggestions", output)

    def test_cli_suggest_repairs_json(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            project, beat = build_ready_project()
            beat.image_prompt = ""
            ProjectService().save_project(project, project_path)
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = cli.main(
                    [
                        "suggest-repairs",
                        "--project",
                        str(project_path),
                        "--episode-id",
                        "ep_001",
                        "--format",
                        "json",
                    ]
                )

            self.assertEqual(exit_code, 0)
            data = json.loads(stdout.getvalue())
            self.assertTrue(data)
            self.assertTrue(any(item["action_type"] == "rebuild_image_prompt" for item in data))

    def test_cli_apply_low_risk_repairs(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            project, beat = build_ready_project()
            beat.review_text = ""
            beat.image_prompt = ""
            beat.negative_prompt = ""
            ProjectService().save_project(project, project_path)

            exit_code = cli.main(
                [
                    "apply-repairs",
                    "--project",
                    str(project_path),
                    "--episode-id",
                    "ep_001",
                    "--low-risk-only",
                    "--save",
                ]
            )

            self.assertEqual(exit_code, 0)
            reloaded = ProjectService().load_project(project_path)
            reloaded_beat = reloaded.review_episodes[0].scenes[0].beats[0]
            self.assertTrue(reloaded_beat.review_text)
            self.assertTrue(reloaded_beat.image_prompt)
            self.assertTrue(reloaded_beat.negative_prompt)


if __name__ == "__main__":
    unittest.main()
