import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.controllers.onboarding_controller import OnboardingController
from app.services.project_service import ProjectService


class OnboardingControllerTests(unittest.TestCase):
    def test_onboarding_controller_creates_and_saves_project(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "project.json"

            project = OnboardingController().create_project(
                "dark_fantasy_webtoon",
                "Onboarded Story",
                output_path,
            )

            self.assertTrue(output_path.exists())
            loaded = ProjectService().load_project(output_path)
            self.assertEqual(project.title, "Onboarded Story")
            self.assertEqual(loaded.title, "Onboarded Story")
            self.assertEqual(loaded.default_art_style, "dark_fantasy_webtoon")
            self.assertTrue(loaded.style_presets)


if __name__ == "__main__":
    unittest.main()
