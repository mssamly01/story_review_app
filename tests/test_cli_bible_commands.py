from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app import cli
from app.services.project_service import ProjectService


class CliBibleCommandTests(unittest.TestCase):
    def test_cli_create_default_style_presets(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            ProjectService().save_project(
                ProjectService().create_project("Bible Story"),
                project_path,
            )

            exit_code = cli.main(
                [
                    "create-default-style-presets",
                    "--project",
                    str(project_path),
                ]
            )

            project = ProjectService().load_project(project_path)
            preset_ids = {style.style_id for style in project.style_presets}
            self.assertEqual(exit_code, 0)
            self.assertIn("dark_fantasy_webtoon", preset_ids)
            self.assertIn("soft_watercolor_webtoon", preset_ids)

    def test_cli_add_character_and_location(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.json"
            ProjectService().save_project(
                ProjectService().create_project("Bible Story"),
                project_path,
            )

            character_exit = cli.main(
                [
                    "add-character",
                    "--project",
                    str(project_path),
                    "--id",
                    "lam_vu",
                    "--name",
                    "Lam Vu",
                    "--aliases",
                    "Vu,young master",
                    "--appearance",
                    "young man",
                    "--default-outfit",
                    "black jacket",
                    "--visual-prompt-base",
                    "young man with messy black hair",
                    "--negative-prompt-terms",
                    "wrong outfit",
                ]
            )
            location_exit = cli.main(
                [
                    "add-location",
                    "--project",
                    str(project_path),
                    "--id",
                    "old_house",
                    "--name",
                    "Old House",
                    "--mood",
                    "mysterious",
                    "--lighting",
                    "moonlight",
                    "--visual-prompt-base",
                    "old countryside house, dusty rooms",
                    "--recurring-props",
                    "locked door,dusty portrait",
                ]
            )

            project = ProjectService().load_project(project_path)
            self.assertEqual(character_exit, 0)
            self.assertEqual(location_exit, 0)
            self.assertEqual(project.characters[0].character_id, "lam_vu")
            self.assertEqual(project.characters[0].aliases, ["Vu", "young master"])
            self.assertEqual(project.locations[0].location_id, "old_house")
            self.assertEqual(project.locations[0].recurring_props, ["locked door", "dusty portrait"])


if __name__ == "__main__":
    unittest.main()
