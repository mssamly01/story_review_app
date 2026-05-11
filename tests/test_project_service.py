import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.services.project_service import ProjectService


class ProjectServiceTests(unittest.TestCase):
    def test_project_can_save_and_load_full_beat_structure(self) -> None:
        service = ProjectService()
        project = service.create_project(
            "Căn nhà cũ",
            genre="dark fantasy",
            default_narration_style="mysterious",
            retelling_density="full",
        )
        chapter = service.add_source_chapter(
            project,
            title="Chương 1",
            chapter_number=1,
            raw_text="Lâm Vũ trở về căn nhà cũ. Cánh cửa cuối hành lang bị khóa.",
        )
        character = service.add_character(
            project,
            name="Lâm Vũ",
            character_id="lam_vu",
            appearance="young man, messy black hair, gray eyes",
            default_outfit="black jacket, white shirt",
            visual_prompt_base=(
                "young man, messy black hair, gray eyes, black jacket, white shirt"
            ),
        )
        location = service.add_location(
            project,
            name="Hành lang nhà cũ",
            location_id="old_house_hallway",
            visual_prompt_base="dusty old hallway, wooden floor, dim moonlight",
        )
        episode = service.add_review_episode(
            project,
            title="Cánh cửa cuối hành lang",
            source_chapter_ids=[chapter.chapter_id],
        )
        scene = service.add_scene(
            project,
            episode_id=episode.episode_id,
            title="Trở về nhà cũ",
            summary="Lâm Vũ bước vào căn nhà cũ và nhận ra có điều bất thường.",
            characters=[character.character_id],
            location=location.location_id,
            mood="mysterious",
        )
        service.add_beat(
            project,
            episode_id=episode.episode_id,
            scene_id=scene.scene_id,
            story_function="opening",
            characters=[character.character_id],
            location=location.location_id,
            action="returns to the old house",
            emotion="uneasy",
            shot_type="wide shot",
            review_text=("Sau nhiều năm xa cách, Lâm Vũ cuối cùng cũng quay lại căn nhà cũ."),
            visual_description="Lâm Vũ đứng trước hành lang phủ bụi.",
            image_prompt=("dark fantasy webtoon style, young man in a dusty old hallway"),
            negative_prompt="low quality, blurry, watermark, text",
            continuity_tags=["lam_vu_black_jacket", "old_house_hallway"],
        )

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.json"
            service.save_project(project, path)
            saved_text = path.read_text(encoding="utf-8")

            loaded = service.load_project(path)

        saved_data = json.loads(saved_text)
        self.assertIn('\n  "project_id":', saved_text)
        self.assertEqual(saved_data["title"], "Căn nhà cũ")
        self.assertEqual(loaded.title, "Căn nhà cũ")
        self.assertEqual(loaded.source_chapters[0].raw_text, chapter.raw_text)
        self.assertEqual(loaded.source_chapters[0].word_count, chapter.word_count)
        loaded_episode = loaded.review_episodes[0]
        self.assertEqual(loaded_episode.source_chapter_ids, [chapter.chapter_id])
        loaded_scene = loaded_episode.scenes[0]
        self.assertEqual(loaded_scene.beat_ids, ["b_001"])
        loaded_beat = loaded_scene.beats[0]
        original_beat = project.review_episodes[0].scenes[0].beats[0]
        self.assertEqual(loaded_beat.review_text, original_beat.review_text)
        self.assertEqual(
            loaded_beat.image_prompt,
            "dark fantasy webtoon style, young man in a dusty old hallway",
        )

    def test_episode_rejects_missing_source_chapter_reference(self) -> None:
        service = ProjectService()
        project = service.create_project("No source")

        with self.assertRaises(LookupError):
            service.add_review_episode(
                project,
                title="Broken episode",
                source_chapter_ids=["ch_missing"],
            )


if __name__ == "__main__":
    unittest.main()
