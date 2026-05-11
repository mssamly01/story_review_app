import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.services.project_service import ProjectService


class ProjectRoundtripTests(unittest.TestCase):
    def test_full_project_roundtrip_preserves_every_collection(self) -> None:
        service = ProjectService()
        project = service.create_project(
            "Căn nhà cũ",
            project_id="project_roundtrip",
            genre="dark fantasy",
            language="vi",
        )
        raw_text = "Dòng một của truyện.\n\nDòng hai phải được giữ nguyên."
        chapter = service.add_source_chapter(
            project,
            chapter_id="ch_001",
            title="Chương 1",
            chapter_number=1,
            raw_text=raw_text,
            notes="Keep source unchanged.",
        )
        character = service.add_character(
            project,
            character_id="lam_vu",
            name="Lâm Vũ",
            visual_prompt_base="young man, black jacket",
        )
        location = service.add_location(
            project,
            location_id="old_house",
            name="Căn nhà cũ",
            visual_prompt_base="old countryside house at dusk",
        )
        style = service.add_style_preset(
            project,
            style_id="dark_fantasy_webtoon",
            name="Dark Fantasy Webtoon",
            positive_prompt="dark fantasy webtoon style",
            negative_prompt="low quality, watermark, text",
        )
        episode = service.add_review_episode(
            project,
            episode_id="ep_001",
            title="Căn nhà cũ",
            source_chapter_ids=[chapter.chapter_id],
            tone="mysterious",
            density="full",
        )
        scene = service.add_scene(
            project,
            episode_id=episode.episode_id,
            scene_id="sc_001",
            title="Trở về",
            summary="Lâm Vũ quay lại căn nhà cũ.",
            characters=[character.character_id],
            location=location.location_id,
            mood="mysterious",
            importance="high",
            target_beats=7,
        )
        service.add_beat(
            project,
            episode_id=episode.episode_id,
            scene_id=scene.scene_id,
            beat_id="b_001",
            order_index=1,
            story_function="opening",
            characters=[character.character_id],
            location=location.location_id,
            action="returns to old house",
            emotion="lonely",
            shot_type="wide shot",
            review_text="Lâm Vũ quay lại căn nhà cũ trong một buổi chiều lạnh.",
            visual_description="Một người trẻ đứng trước căn nhà cũ.",
            image_prompt="dark fantasy webtoon style, old house at dusk",
            negative_prompt="low quality, blurry, text",
            continuity_tags=["old_house", "dusk"],
        )

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.json"
            service.save_project(project, path)
            saved_text = path.read_text(encoding="utf-8")
            loaded_project = service.load_project(path)

        self.assertTrue(saved_text.startswith("{\n  "))
        saved_data = json.loads(saved_text)
        self.assertEqual(
            list(saved_data.keys())[:7],
            [
                "project_id",
                "title",
                "author_source_note",
                "genre",
                "language",
                "default_narration_style",
                "default_art_style",
            ],
        )

        self.assertEqual(len(loaded_project.source_chapters), 1)
        self.assertEqual(len(loaded_project.review_episodes), 1)
        self.assertEqual(len(loaded_project.characters), 1)
        self.assertEqual(len(loaded_project.locations), 1)
        self.assertEqual(len(loaded_project.style_presets), 1)

        loaded_chapter = loaded_project.source_chapters[0]
        loaded_episode = loaded_project.review_episodes[0]
        loaded_scene = loaded_episode.scenes[0]
        loaded_beat = loaded_scene.beats[0]

        self.assertEqual(loaded_chapter.raw_text, raw_text)
        self.assertEqual(loaded_chapter.notes, "Keep source unchanged.")
        self.assertEqual(loaded_episode.source_chapter_ids, ["ch_001"])
        self.assertEqual(loaded_episode.scene_ids, ["sc_001"])
        self.assertEqual(loaded_scene.beat_ids, ["b_001"])
        self.assertEqual(loaded_scene.target_beats, 7)
        self.assertEqual(
            loaded_beat.review_text,
            "Lâm Vũ quay lại căn nhà cũ trong một buổi chiều lạnh.",
        )
        self.assertEqual(loaded_beat.image_prompt, "dark fantasy webtoon style, old house at dusk")
        self.assertEqual(loaded_project.characters[0].character_id, character.character_id)
        self.assertEqual(loaded_project.locations[0].location_id, location.location_id)
        self.assertEqual(loaded_project.style_presets[0].style_id, style.style_id)

    def test_project_json_serialization_is_stable_from_loaded_model(self) -> None:
        service = ProjectService()
        project = service.create_project("Căn nhà cũ", project_id="project_stable")
        service.add_source_chapter(
            project,
            title="Chương 1",
            chapter_number=1,
            raw_text="Raw text must remain stable.",
        )

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.json"
            service.save_project(project, path)
            loaded_project = service.load_project(path)

        first_json = json.dumps(
            loaded_project.to_dict(),
            ensure_ascii=False,
            indent=2,
        )
        second_json = json.dumps(
            loaded_project.to_dict(),
            ensure_ascii=False,
            indent=2,
        )
        self.assertEqual(first_json, second_json)
        self.assertIn('"raw_text": "Raw text must remain stable."', first_json)


if __name__ == "__main__":
    unittest.main()
