import importlib
import unittest

from app.services.export_service import ExportService
from app.services.project_service import ProjectService


def optional_class(module_name: str, class_name: str):
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        return None
    return getattr(module, class_name, None)


SourceImportService = optional_class(
    "app.services.source_import_service",
    "SourceImportService",
)
StoryParserService = optional_class(
    "app.services.story_parser_service",
    "StoryParserService",
)
EpisodePlannerService = optional_class(
    "app.services.episode_planner_service",
    "EpisodePlannerService",
)


class PhaseOneToFourWorkflowTests(unittest.TestCase):
    def test_source_import_service_imports_without_side_effects(self) -> None:
        if SourceImportService is None:
            self.skipTest("SourceImportService is not implemented.")

        project_service = ProjectService()
        import_service = SourceImportService(project_service)
        project = project_service.create_project("Căn nhà cũ")
        raw_text = "Lâm Vũ trở về căn nhà cũ."

        chapter = import_service.import_raw_text(
            project,
            title="Chương 1",
            chapter_number=1,
            raw_text=raw_text,
        )

        self.assertEqual(chapter.raw_text, raw_text)
        self.assertEqual(chapter.word_count, len(raw_text.split()))
        self.assertEqual(project.source_chapters, [chapter])
        self.assertEqual(project.review_episodes, [])
        self.assertEqual(project.characters, [])
        self.assertEqual(project.locations, [])

    def test_story_parser_service_returns_structured_mock_data(self) -> None:
        if StoryParserService is None:
            self.skipTest("StoryParserService is not implemented.")

        project_service = ProjectService()
        project = project_service.create_project("Căn nhà cũ")
        raw_text = (
            "Lâm Vũ trở về căn nhà cũ. "
            "Anh phát hiện căn phòng bị khóa ở hành lang cuối."
        )
        chapter = project_service.add_source_chapter(
            project,
            title="Chương 1",
            chapter_number=1,
            raw_text=raw_text,
        )
        parser = StoryParserService()

        result = parser.parse(chapter)
        data = result.to_dict()

        self.assertIsInstance(data, dict)
        self.assertIn("detected_characters", data)
        self.assertIn("detected_locations", data)
        self.assertIn("scene_candidates", data)
        self.assertIn("important_events", data)
        self.assertNotEqual(data["detected_characters"], [])
        self.assertNotEqual(data["detected_locations"], [])
        self.assertNotEqual(data["scene_candidates"], [])
        self.assertNotEqual(data["important_events"], [])
        self.assertEqual(chapter.raw_text, raw_text)

    def test_episode_planner_creates_structured_episode_not_short_summary(self) -> None:
        if EpisodePlannerService is None:
            self.skipTest("EpisodePlannerService is not implemented.")

        project_service = ProjectService()
        planner = EpisodePlannerService(project_service)
        project = project_service.create_project("Căn nhà cũ")
        raw_text = (
            "Lâm Vũ trở về căn nhà cũ sau nhiều năm xa cách. "
            "Anh nghe thấy một tiếng động kỳ lạ ở hành lang cuối.\n\n"
            "Lâm Vũ phát hiện căn phòng bị khóa. "
            "Ông Nội xuất hiện sau lưng anh."
        )
        chapter = project_service.add_source_chapter(
            project,
            title="Chương 1",
            chapter_number=1,
            raw_text=raw_text,
        )

        episode = planner.plan_episode(
            project,
            selected_source_chapter_ids=[chapter.chapter_id],
            narration_style="mysterious",
            retelling_density="full",
        )

        self.assertEqual(episode.source_chapter_ids, [chapter.chapter_id])
        self.assertEqual(episode.tone, "mysterious")
        self.assertEqual(episode.density, "full")
        self.assertGreaterEqual(len(episode.scenes), 2)
        self.assertTrue(all(scene.title for scene in episode.scenes))
        self.assertTrue(all(scene.summary for scene in episode.scenes))
        self.assertTrue(all(scene.target_beats >= 5 for scene in episode.scenes))
        self.assertNotEqual(episode.scene_ids, [])
        self.assertNotEqual(episode.summary, raw_text)
        self.assertEqual(chapter.raw_text, raw_text)

    def test_phase_1_to_4_manual_beat_export_workflow(self) -> None:
        project_service = ProjectService()
        export_service = ExportService(project_service)
        project = project_service.create_project("Căn nhà cũ")
        chapter = project_service.add_source_chapter(
            project,
            title="Chương 1",
            chapter_number=1,
            raw_text="Lâm Vũ trở về căn nhà cũ.",
        )
        episode = project_service.add_review_episode(
            project,
            title="Cánh cửa cuối hành lang",
            source_chapter_ids=[chapter.chapter_id],
            tone="mysterious",
            density="full",
        )
        scene = project_service.add_scene(
            project,
            episode_id=episode.episode_id,
            title="Trở về",
            summary="Lâm Vũ quay lại căn nhà cũ.",
            characters=["lam_vu"],
            location="old_house",
            mood="mysterious",
        )
        project_service.add_beat(
            project,
            episode_id=episode.episode_id,
            scene_id=scene.scene_id,
            story_function="opening",
            characters=["lam_vu"],
            location="old_house",
            action="returns to old house",
            emotion="lonely",
            shot_type="wide shot",
            review_text="Lâm Vũ quay lại căn nhà mà ông nội để lại.",
            visual_description="Lâm Vũ đứng trước căn nhà cũ vào chiều tối.",
            image_prompt="dark fantasy webtoon style, old house at dusk",
            negative_prompt="low quality, blurry, text, watermark",
            continuity_tags=["lam_vu", "old_house", "dusk"],
        )

        markdown = export_service.export_episode_to_markdown(
            project,
            episode.episode_id,
        )
        second_markdown = export_service.export_episode_to_markdown(
            project,
            episode.episode_id,
        )

        self.assertEqual(markdown, second_markdown)
        self.assertIn("# Cánh cửa cuối hành lang", markdown)
        self.assertIn("## Scene 1 - Trở về", markdown)
        self.assertIn("Lâm Vũ quay lại căn nhà mà ông nội để lại.", markdown)
        self.assertIn("dark fantasy webtoon style, old house at dusk", markdown)
        self.assertIn("low quality, blurry, text, watermark", markdown)


if __name__ == "__main__":
    unittest.main()
