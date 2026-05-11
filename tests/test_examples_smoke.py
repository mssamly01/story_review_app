"""Smoke tests for files shipped in ``examples/``.

If the example project ever stops loading, those tutorials in the README and in
``examples/README.md`` are silently broken. These tests keep the sample honest.
"""

import unittest
from pathlib import Path

from app.services.project_service import ProjectService

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


class ExampleProjectsSmokeTests(unittest.TestCase):
    def test_can_nha_cu_loads_and_validates(self) -> None:
        path = EXAMPLES_DIR / "can_nha_cu.json"
        self.assertTrue(path.exists(), f"expected sample file at {path}")

        project = ProjectService().load_project(path)

        self.assertEqual(project.project_id, "example_can_nha_cu")
        self.assertEqual(project.title, "Căn nhà cũ")
        self.assertEqual(len(project.source_chapters), 1)
        self.assertEqual(len(project.characters), 1)
        self.assertEqual(len(project.locations), 1)
        self.assertEqual(len(project.style_presets), 1)
        self.assertEqual(len(project.review_episodes), 1)

        beats = [
            beat
            for episode in project.review_episodes
            for scene in episode.scenes
            for beat in scene.beats
        ]
        self.assertGreaterEqual(len(beats), 3, "sample should have at least 3 beats")
        for beat in beats:
            self.assertTrue(beat.review_text, f"beat {beat.beat_id} missing review_text")
            self.assertTrue(beat.image_prompt, f"beat {beat.beat_id} missing image_prompt")


if __name__ == "__main__":
    unittest.main()
