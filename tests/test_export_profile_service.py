import csv
import json
import unittest
from tempfile import TemporaryDirectory

from app.services.export_profile_service import ExportProfileService
from tests.test_production_readiness_service import (
    build_ready_project,
    duplicate_episode,
)

REQUIRED_PROFILE_IDS = {
    "production_markdown",
    "youtube_review_script",
    "shorts_review_script",
    "image_prompt_csv",
    "prompt_only_txt",
    "review_only_txt",
    "full_json_handoff",
    "batch_package",
    "quality_report_package",
}


class ExportProfileServiceTests(unittest.TestCase):
    def test_list_profiles_contains_required_profiles(self) -> None:
        profiles = ExportProfileService().list_profiles()

        self.assertEqual({profile.profile_id for profile in profiles}, REQUIRED_PROFILE_IDS)

    def test_get_profile_returns_profile(self) -> None:
        profile = ExportProfileService().get_profile("production_markdown")

        self.assertEqual(profile.profile_id, "production_markdown")
        self.assertTrue(profile.name)
        self.assertTrue(profile.description)
        self.assertTrue(profile.formats)

    def test_export_episode_production_markdown(self) -> None:
        project, beat = build_ready_project()
        with TemporaryDirectory() as temp_dir:
            paths = ExportProfileService().export_episode_with_profile(
                project,
                "ep_001",
                "production_markdown",
                temp_dir,
            )

            self.assertEqual(len(paths), 1)
            content = paths[0].read_text(encoding="utf-8")
            self.assertIn("Episode 1", content)
            self.assertIn(beat.review_text, content)
            self.assertIn(beat.image_prompt, content)
            self.assertIn(beat.negative_prompt, content)

    def test_export_episode_youtube_review_script_excludes_prompts(self) -> None:
        project, beat = build_ready_project()
        with TemporaryDirectory() as temp_dir:
            paths = ExportProfileService().export_episode_with_profile(
                project,
                "ep_001",
                "youtube_review_script",
                temp_dir,
            )

            content = paths[0].read_text(encoding="utf-8")
            self.assertIn(beat.review_text, content)
            self.assertNotIn(beat.image_prompt, content)
            self.assertNotIn(beat.negative_prompt, content)

    def test_export_episode_image_prompt_csv(self) -> None:
        project, _beat = build_ready_project()
        with TemporaryDirectory() as temp_dir:
            paths = ExportProfileService().export_episode_with_profile(
                project,
                "ep_001",
                "image_prompt_csv",
                temp_dir,
            )

            with paths[0].open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            self.assertEqual(
                set(rows[0]),
                {
                    "beat_id",
                    "scene_id",
                    "image_prompt",
                    "negative_prompt",
                    "characters",
                    "location",
                    "shot_type",
                },
            )

    def test_export_episode_full_json_handoff_serializable(self) -> None:
        project, _beat = build_ready_project()
        with TemporaryDirectory() as temp_dir:
            paths = ExportProfileService().export_episode_with_profile(
                project,
                "ep_001",
                "full_json_handoff",
                temp_dir,
            )

            data = json.loads(paths[0].read_text(encoding="utf-8"))
            json.dumps(data)
            self.assertIn("episode", data)
            self.assertIn("scenes", data)
            self.assertIn("beats", data)
            self.assertIn("quality", data)
            self.assertIn("readiness", data)

    def test_export_quality_report_package(self) -> None:
        project, _beat = build_ready_project()
        with TemporaryDirectory() as temp_dir:
            paths = ExportProfileService().export_episode_with_profile(
                project,
                "ep_001",
                "quality_report_package",
                temp_dir,
            )

            names = {path.name for path in paths}
            self.assertIn("episode_001_prompt_quality.md", names)
            self.assertIn("episode_001_review_quality.md", names)
            self.assertIn("episode_001_readiness.md", names)
            self.assertTrue(all(path.exists() for path in paths))

    def test_export_batch_package_multiple_episodes(self) -> None:
        project, _beat = build_ready_project()
        duplicate_episode(project, source_episode_id="ep_001", new_episode_id="ep_002")
        with TemporaryDirectory() as temp_dir:
            paths = ExportProfileService().export_batch_with_profile(
                project,
                ["ep_001", "ep_002"],
                "batch_package",
                temp_dir,
            )

            self.assertEqual(len(paths), 10)
            names = {path.name for path in paths}
            self.assertIn("episode_001_production.md", names)
            self.assertIn("episode_002_production.md", names)

    def test_export_profile_does_not_modify_project(self) -> None:
        project, _beat = build_ready_project()
        before = project.to_dict()
        service = ExportProfileService()
        with TemporaryDirectory() as temp_dir:
            for profile_id in REQUIRED_PROFILE_IDS:
                service.export_episode_with_profile(project, "ep_001", profile_id, temp_dir)

        self.assertEqual(project.to_dict(), before)

    def test_export_profile_handles_missing_optional_quality_services_gracefully(self) -> None:
        project, beat = build_ready_project()
        beat.image_prompt = ""
        beat.negative_prompt = ""
        with TemporaryDirectory() as temp_dir:
            paths = ExportProfileService().export_episode_with_profile(
                project,
                "ep_001",
                "quality_report_package",
                temp_dir,
            )

            self.assertEqual(len(paths), 3)
            self.assertTrue(all(path.exists() for path in paths))


if __name__ == "__main__":
    unittest.main()
