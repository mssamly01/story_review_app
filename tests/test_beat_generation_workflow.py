import unittest

from app.services.beat_generator_service import BeatGeneratorService
from app.services.episode_planner_service import EpisodePlannerService
from app.services.export_service import ExportService
from app.services.project_service import ProjectService


class BeatGenerationWorkflowTests(unittest.TestCase):
    def test_planned_episode_can_generate_beat_plans(self) -> None:
        project_service = ProjectService()
        planner = EpisodePlannerService(project_service)
        generator = BeatGeneratorService(project_service)
        export_service = ExportService(project_service)
        project = project_service.create_project("Căn nhà cũ")
        chapter = project_service.add_source_chapter(
            project,
            title="Chương 1",
            chapter_number=1,
            raw_text=(
                "Lâm Vũ trở về căn nhà cũ sau nhiều năm xa cách. "
                "Anh nghe thấy một tiếng động kỳ lạ ở hành lang cuối.\n\n"
                "Lâm Vũ phát hiện căn phòng bị khóa. "
                "Ông Nội xuất hiện sau lưng anh."
            ),
        )
        episode = planner.plan_episode(
            project,
            selected_source_chapter_ids=[chapter.chapter_id],
            narration_style="mysterious",
            retelling_density="full",
        )

        beats = generator.generate_beats_for_episode(project, episode.episode_id)

        self.assertGreater(len(beats), 0)
        self.assertTrue(all(scene.beats for scene in episode.scenes))
        self.assertTrue(all(beat.review_text == "" for beat in beats))
        self.assertTrue(all(beat.image_prompt == "" for beat in beats))
        self.assertTrue(all(beat.negative_prompt == "" for beat in beats))

        markdown = export_service.export_episode_to_markdown(
            project,
            episode.episode_id,
        )
        self.assertIn("_Not written yet._", markdown)
        self.assertIn("_Not generated yet._", markdown)
        self.assertEqual(chapter.raw_text, project.source_chapters[0].raw_text)


if __name__ == "__main__":
    unittest.main()
