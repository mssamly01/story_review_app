import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from app import cli
from app.services.project_service import ProjectService
from tests.test_project_validation_service import build_complete_project


class PhaseThirteenValidationWorkflowTests(unittest.TestCase):
    def test_cli_validate_project_text_output(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            project = build_complete_project()
            project.review_episodes[0].scenes[0].beats[0].image_prompt = ""
            ProjectService().save_project(project, project_path)
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = cli.main(
                    [
                        "validate-project",
                        "--project",
                        str(project_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            output = stdout.getvalue()
            self.assertIn("Validation issues", output)
            self.assertIn("empty_image_prompt", output)

    def test_cli_validate_project_json_output(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            project = build_complete_project()
            project.review_episodes[0].scenes[0].beats[0].review_text = ""
            ProjectService().save_project(project, project_path)
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = cli.main(
                    [
                        "validate-project",
                        "--project",
                        str(project_path),
                        "--format",
                        "json",
                    ]
                )

            self.assertEqual(exit_code, 0)
            data = json.loads(stdout.getvalue())
            self.assertIsInstance(data, list)
            self.assertTrue(any(issue["category"] == "empty_review_text" for issue in data))

    def test_cli_validate_project_fail_on_error(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            project_service = ProjectService()
            project = project_service.create_project("Broken Story")
            project_service.add_source_chapter(
                project,
                title="Chapter 1",
                chapter_number=1,
                raw_text="",
            )
            project_service.save_project(project, project_path)
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = cli.main(
                    [
                        "validate-project",
                        "--project",
                        str(project_path),
                        "--fail-on-error",
                    ]
                )

            self.assertNotEqual(exit_code, 0)
            self.assertIn("source_raw_text_missing", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
