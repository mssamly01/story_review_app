import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.services.episode_planner_service import EpisodePlannerService
from app.services.project_service import ProjectService


class EpisodePlannerServiceTests(unittest.TestCase):
    def test_plan_episode_creates_review_episode_with_scene_objects(self) -> None:
        project_service = ProjectService()
        planner = EpisodePlannerService(project_service)
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

        self.assertEqual(episode.title, "Review: Chương 1")
        self.assertEqual(episode.source_chapter_ids, ["ch_001"])
        self.assertEqual(episode.tone, "mysterious")
        self.assertEqual(episode.density, "full")
        self.assertEqual(episode.status, "planned")
        self.assertEqual(project.review_episodes, [episode])
        self.assertEqual(len(episode.scenes), 2)
        self.assertEqual(chapter.parsed_scene_ids, episode.scene_ids)

        first_scene = episode.scenes[0]
        self.assertEqual(first_scene.scene_id, "sc_001")
        self.assertEqual(first_scene.episode_id, episode.episode_id)
        self.assertEqual(first_scene.characters, ["Lâm Vũ"])
        self.assertEqual(first_scene.location, "căn nhà cũ")
        self.assertEqual(first_scene.mood, "mysterious")
        self.assertEqual(first_scene.importance, "high")
        self.assertGreaterEqual(first_scene.target_beats, 6)
        self.assertEqual(first_scene.beats, [])
        self.assertIn("retell this scene in detail", first_scene.summary)
        self.assertIn("Important events to preserve:", first_scene.summary)
        self.assertGreaterEqual(episode.estimated_beats, first_scene.target_beats)

    def test_plan_episode_preserves_selected_chapter_order(self) -> None:
        project_service = ProjectService()
        planner = EpisodePlannerService(project_service)
        project = project_service.create_project("Căn nhà cũ")
        first_chapter = project_service.add_source_chapter(
            project,
            title="Chương 1",
            chapter_number=1,
            raw_text="Lâm Vũ bước vào căn nhà cũ.",
        )
        second_chapter = project_service.add_source_chapter(
            project,
            title="Chương 2",
            chapter_number=2,
            raw_text="Ông Nội mở căn phòng bị khóa.",
        )

        episode = planner.plan_episode(
            project,
            selected_source_chapter_ids=[
                second_chapter.chapter_id,
                first_chapter.chapter_id,
            ],
            narration_style="dramatic",
            retelling_density="balanced",
            episode_title="Căn phòng bị khóa",
        )

        self.assertEqual(episode.title, "Căn phòng bị khóa")
        self.assertEqual(episode.source_chapter_ids, ["ch_002", "ch_001"])
        self.assertIn("ch_002 - Chương 2", episode.scenes[0].summary)
        self.assertIn("ch_001 - Chương 1", episode.scenes[-1].summary)
        self.assertEqual(second_chapter.parsed_scene_ids, ["sc_001"])
        self.assertEqual(first_chapter.parsed_scene_ids, ["sc_002"])

    def test_planned_episode_persists_scene_plan_fields(self) -> None:
        project_service = ProjectService()
        planner = EpisodePlannerService(project_service)
        project = project_service.create_project("Căn nhà cũ")
        chapter = project_service.add_source_chapter(
            project,
            title="Chương 1",
            chapter_number=1,
            raw_text="Lâm Vũ phát hiện căn phòng bị khóa.",
        )
        episode = planner.plan_episode(
            project,
            selected_source_chapter_ids=[chapter.chapter_id],
            narration_style="neutral",
            retelling_density="condensed",
        )

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.json"
            project_service.save_project(project, path)
            loaded_project = project_service.load_project(path)

        loaded_episode = loaded_project.review_episodes[0]
        loaded_scene = loaded_episode.scenes[0]
        self.assertEqual(loaded_episode.episode_id, episode.episode_id)
        self.assertEqual(loaded_scene.importance, "high")
        self.assertEqual(loaded_scene.target_beats, episode.scenes[0].target_beats)
        self.assertEqual(loaded_episode.estimated_beats, loaded_scene.target_beats)

    def test_plan_episode_rejects_invalid_inputs(self) -> None:
        project_service = ProjectService()
        planner = EpisodePlannerService(project_service)
        project = project_service.create_project("Căn nhà cũ")
        chapter = project_service.add_source_chapter(
            project,
            title="Chương 1",
            chapter_number=1,
            raw_text="Lâm Vũ trở về căn nhà cũ.",
        )

        with self.assertRaises(ValueError):
            planner.plan_episode(
                project,
                selected_source_chapter_ids=[],
                narration_style="mysterious",
                retelling_density="full",
            )

        with self.assertRaises(ValueError):
            planner.plan_episode(
                project,
                selected_source_chapter_ids=[chapter.chapter_id],
                narration_style="epic",
                retelling_density="full",
            )

        with self.assertRaises(ValueError):
            planner.plan_episode(
                project,
                selected_source_chapter_ids=[chapter.chapter_id],
                narration_style="mysterious",
                retelling_density="summary",
            )

        with self.assertRaises(LookupError):
            planner.plan_episode(
                project,
                selected_source_chapter_ids=["ch_missing"],
                narration_style="mysterious",
                retelling_density="full",
            )


if __name__ == "__main__":
    unittest.main()
