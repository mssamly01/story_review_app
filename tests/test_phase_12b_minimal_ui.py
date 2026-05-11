import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from app.controllers.export_controller import ExportController
from app.controllers.generation_controller import GenerationController
from app.controllers.project_controller import ProjectController
from app.infrastructure.openai_ai_gateway import AIConfigurationError
from app.services.project_service import ProjectService


class PhaseTwelveBMinimalUITests(unittest.TestCase):
    def test_controllers_can_create_and_save_project(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.json"
            controller = ProjectController()

            controller.create_project("Demo Story", output_path=path)
            loaded = controller.open_project(path)

            self.assertEqual(loaded.title, "Demo Story")

    def test_generation_controller_deterministic_pipeline(self) -> None:
        project_service = ProjectService()
        project = project_service.create_project("Demo Story")
        chapter = project_service.add_source_chapter(
            project,
            title="Chapter 1",
            chapter_number=1,
            raw_text="Lan returns to the old house. She finds a clue.",
        )
        controller = GenerationController(project_service)

        episode = controller.run_full_pipeline(
            project,
            chapter_id=chapter.chapter_id,
            episode_title="Episode 1",
            tone="mysterious",
            density="full",
        )

        beats = [beat for scene in episode.scenes for beat in scene.beats]
        self.assertTrue(episode.scenes)
        self.assertTrue(beats)
        self.assertTrue(all(beat.review_text for beat in beats))
        self.assertTrue(all(beat.image_prompt for beat in beats))

    def test_generation_controller_mock_ai_pipeline(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            project_service = ProjectService()
            project = project_service.create_project("Demo Story")
            chapter = project_service.add_source_chapter(
                project,
                title="Chapter 1",
                chapter_number=1,
                raw_text="Lan returns to the old house and finds a clue.",
            )
            controller = GenerationController(project_service)

            episode = controller.run_full_pipeline(
                project,
                chapter_id=chapter.chapter_id,
                episode_title="Episode 1",
                tone="mysterious",
                density="full",
                ai_mode="mock",
            )

        beats = [beat for scene in episode.scenes for beat in scene.beats]
        self.assertEqual(episode.title, "Mock Review Episode")
        self.assertTrue(beats)
        self.assertTrue(all(beat.review_text for beat in beats))
        self.assertTrue(all(beat.image_prompt for beat in beats))

    def test_export_controller_exports_selected_episode(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_service, project, episode_id = self._build_export_project()
            controller = ExportController(project_service)
            formats = {
                "markdown": "episode.md",
                "json": "episode.json",
                "csv": "episode.csv",
                "review-txt": "review.txt",
                "prompts-txt": "prompts.txt",
            }

            for export_format, filename in formats.items():
                with self.subTest(export_format=export_format):
                    path = Path(temp_dir) / filename
                    controller.export_episode(
                        project,
                        episode_id,
                        export_format=export_format,
                        output_path=path,
                    )
                    self.assertTrue(path.exists())
                    self.assertNotEqual(path.read_text(encoding="utf-8").strip(), "")

    def test_real_ai_missing_credentials_shows_clear_error(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            project_service = ProjectService()
            project = project_service.create_project("Demo Story")
            chapter = project_service.add_source_chapter(
                project,
                title="Chapter 1",
                chapter_number=1,
                raw_text="Lan returns to the old house.",
            )
            controller = GenerationController(project_service)

            with self.assertRaises(AIConfigurationError):
                controller.parse_story(
                    project,
                    chapter.chapter_id,
                    ai_mode="real",
                )

    def _build_export_project(self):
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
            summary="Lan finds a clue.",
        )
        project_service.add_beat(
            project,
            episode_id=episode.episode_id,
            scene_id=scene.scene_id,
            beat_id="b_001",
            order_index=1,
            story_function="discovery",
            review_text="Lan notices the clue.",
            visual_description="a clue on a dusty floor",
            image_prompt="webtoon style, clue on dusty floor",
            negative_prompt="low quality, text, watermark, logo",
        )
        return project_service, project, episode.episode_id


if __name__ == "__main__":
    unittest.main()
