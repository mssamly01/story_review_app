import csv
import io
import json
import unittest

from app.services.export_service import ExportService
from app.services.project_service import ProjectService


def build_export_project():
    project_service = ProjectService()
    project = project_service.create_project(
        "The Old House",
        project_id="project_export",
        default_art_style="dark fantasy webtoon",
        retelling_density="full",
    )
    chapter = project_service.add_source_chapter(
        project,
        chapter_id="ch_001",
        title="Chapter 1",
        chapter_number=1,
        raw_text='Linh returns to the old house.\nThe locked door says, "wait."',
    )
    character = project_service.add_character(
        project,
        character_id="linh",
        name="Linh",
        visual_prompt_base="young detective, navy coat, silver flashlight",
    )
    location = project_service.add_location(
        project,
        location_id="old_hall",
        name="Old Hall",
        visual_prompt_base="dusty hallway, cracked walls, moonlit floor",
    )
    style = project_service.add_style_preset(
        project,
        style_id="dark_fantasy_webtoon",
        name="Dark Fantasy Webtoon",
        positive_prompt="dark fantasy webtoon style, cinematic lighting",
        negative_prompt="low quality, text, watermark, logo",
    )
    episode = project_service.add_review_episode(
        project,
        episode_id="ep_001",
        title="The Door at the End",
        source_chapter_ids=[chapter.chapter_id],
        tone="mysterious",
        density="full",
        summary="Linh follows a strange sound through the house.",
    )
    first_scene = project_service.add_scene(
        project,
        episode_id=episode.episode_id,
        scene_id="sc_001",
        title="Return to the Hall",
        summary="Linh enters the hallway and finds signs that someone is inside.",
        characters=[character.character_id],
        location=location.location_id,
        mood="uneasy",
    )
    second_scene = project_service.add_scene(
        project,
        episode_id=episode.episode_id,
        scene_id="sc_002",
        title="The Locked Door",
        summary="The locked door moves before Linh can touch it.",
        characters=[character.character_id],
        location=location.location_id,
        mood="tense",
    )
    project_service.add_beat(
        project,
        episode_id=episode.episode_id,
        scene_id=first_scene.scene_id,
        beat_id="b_002",
        order_index=2,
        story_function="reaction",
        characters=[character.character_id],
        location=location.location_id,
        action="hears a floorboard crack behind her",
        emotion="shocked",
        shot_type="close-up",
        review_text="Linh freezes as a floorboard cracks behind her.",
        visual_description="Linh turning toward a dark hallway corner",
        image_prompt="dark fantasy webtoon style, Linh turns toward the sound",
        negative_prompt="low quality, blurry, text, watermark, logo",
        continuity_tags=["linh", "old_hall", "night"],
    )
    project_service.add_beat(
        project,
        episode_id=episode.episode_id,
        scene_id=first_scene.scene_id,
        beat_id="b_001",
        order_index=1,
        story_function="discovery",
        characters=[character.character_id],
        location=location.location_id,
        action="finds fresh footprints in dust",
        emotion="curious",
        shot_type="detail shot",
        review_text='Linh pauses, listens,\nand notices the door marked "open."',
        visual_description="fresh footprints crossing the dusty wooden floor",
        image_prompt="dark fantasy webtoon style, fresh footprints in dust",
        negative_prompt="low quality, blurry, text, watermark, logo",
        continuity_tags=["linh", "old_hall", "footprints"],
    )
    project_service.add_beat(
        project,
        episode_id=episode.episode_id,
        scene_id=second_scene.scene_id,
        beat_id="b_003",
        order_index=1,
        story_function="cliffhanger",
        characters=[character.character_id],
        location=location.location_id,
        action="the locked door opens by itself",
        emotion="fearful",
        shot_type="wide shot",
        review_text="The locked door slowly opens before Linh raises her hand.",
        visual_description="old door opening into a black room",
        image_prompt="dark fantasy webtoon style, old door opening by itself",
        negative_prompt="low quality, blurry, text, watermark, logo",
        continuity_tags=["linh", "old_hall", "locked_door"],
    )
    return {
        "project": project,
        "chapter": chapter,
        "episode": episode,
        "first_scene": first_scene,
        "second_scene": second_scene,
        "character": character,
        "location": location,
        "style": style,
    }


class ExportPipelineTests(unittest.TestCase):
    def test_export_episode_markdown_full_content(self) -> None:
        sample = build_export_project()
        project = sample["project"]
        episode = sample["episode"]
        markdown = ExportService().export_episode_markdown(
            project,
            episode.episode_id,
        )

        self.assertIn("The Old House", markdown)
        self.assertIn("The Door at the End", markdown)
        self.assertIn("Return to the Hall", markdown)
        self.assertIn("b_001", markdown)
        self.assertIn('notices the door marked "open."', markdown)
        self.assertIn("fresh footprints crossing the dusty wooden floor", markdown)
        self.assertIn("dark fantasy webtoon style, fresh footprints in dust", markdown)
        self.assertIn("low quality, blurry, text, watermark, logo", markdown)
        self.assertIn("footprints", markdown)

    def test_export_episode_json_is_structured_and_serializable(self) -> None:
        sample = build_export_project()
        project = sample["project"]
        episode = sample["episode"]
        data = ExportService().export_episode_json(project, episode.episode_id)

        self.assertIsInstance(data, dict)
        json.dumps(data)
        self.assertIn("episode", data)
        self.assertIn("scenes", data)
        self.assertIn("beats", data)
        self.assertEqual(data["episode"]["episode_id"], episode.episode_id)
        self.assertEqual(len(data["scenes"]), 2)
        self.assertEqual(len(data["beats"]), 3)
        self.assertEqual(data["characters"][0]["character_id"], "linh")
        self.assertEqual(data["locations"][0]["location_id"], "old_hall")
        self.assertEqual(data["style_preset"]["style_id"], "dark_fantasy_webtoon")
        self.assertIn("review_text", data["beats"][0])
        self.assertIn("image_prompt", data["beats"][0])
        self.assertIn("negative_prompt", data["beats"][0])

    def test_export_episode_csv_has_expected_columns(self) -> None:
        sample = build_export_project()
        project = sample["project"]
        episode = sample["episode"]
        csv_text = ExportService().export_episode_csv(project, episode.episode_id)
        rows = list(csv.DictReader(io.StringIO(csv_text)))

        self.assertEqual(
            list(rows[0].keys()),
            ExportService.CSV_COLUMNS,
        )
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["beat_id"], "b_001")
        self.assertEqual(
            rows[0]["review_text"],
            'Linh pauses, listens,\nand notices the door marked "open."',
        )

    def test_export_review_script_txt_excludes_prompts(self) -> None:
        sample = build_export_project()
        project = sample["project"]
        episode = sample["episode"]
        text = ExportService().export_review_script_txt(project, episode.episode_id)

        self.assertIn("The Door at the End", text)
        self.assertIn("Return to the Hall", text)
        self.assertIn("Linh pauses, listens,", text)
        self.assertNotIn("dark fantasy webtoon style, fresh footprints in dust", text)
        self.assertNotIn("low quality, blurry, text, watermark, logo", text)

    def test_export_image_prompts_txt_excludes_review_script(self) -> None:
        sample = build_export_project()
        project = sample["project"]
        episode = sample["episode"]
        text = ExportService().export_image_prompts_txt(project, episode.episode_id)

        self.assertIn("The Door at the End", text)
        self.assertIn("Beat ID: b_001", text)
        self.assertIn("dark fantasy webtoon style, fresh footprints in dust", text)
        self.assertIn("low quality, blurry, text, watermark, logo", text)
        self.assertNotIn("Linh pauses, listens,", text)

    def test_exports_are_deterministic(self) -> None:
        sample = build_export_project()
        project = sample["project"]
        episode = sample["episode"]
        service = ExportService()

        self.assertEqual(
            service.export_episode_markdown(project, episode.episode_id),
            service.export_episode_markdown(project, episode.episode_id),
        )
        self.assertEqual(
            service.export_episode_json(project, episode.episode_id),
            service.export_episode_json(project, episode.episode_id),
        )
        self.assertEqual(
            service.export_episode_csv(project, episode.episode_id),
            service.export_episode_csv(project, episode.episode_id),
        )
        self.assertEqual(
            service.export_review_script_txt(project, episode.episode_id),
            service.export_review_script_txt(project, episode.episode_id),
        )
        self.assertEqual(
            service.export_image_prompts_txt(project, episode.episode_id),
            service.export_image_prompts_txt(project, episode.episode_id),
        )

    def test_exports_do_not_modify_project(self) -> None:
        sample = build_export_project()
        project = sample["project"]
        episode = sample["episode"]
        before = project.to_dict()
        service = ExportService()

        service.export_episode_markdown(project, episode.episode_id)
        service.export_episode_json(project, episode.episode_id)
        service.export_episode_csv(project, episode.episode_id)
        service.export_review_script_txt(project, episode.episode_id)
        service.export_image_prompts_txt(project, episode.episode_id)

        self.assertEqual(project.to_dict(), before)

    def test_exports_preserve_source_raw_text(self) -> None:
        sample = build_export_project()
        project = sample["project"]
        episode = sample["episode"]
        chapter = sample["chapter"]
        raw_text = chapter.raw_text
        service = ExportService()

        service.export_episode_markdown(project, episode.episode_id)
        service.export_episode_json(project, episode.episode_id)
        service.export_episode_csv(project, episode.episode_id)
        service.export_review_script_txt(project, episode.episode_id)
        service.export_image_prompts_txt(project, episode.episode_id)

        self.assertEqual(chapter.raw_text, raw_text)

    def test_export_orders_beats_by_scene_and_order_index(self) -> None:
        sample = build_export_project()
        project = sample["project"]
        episode = sample["episode"]
        markdown = ExportService().export_episode_markdown(
            project,
            episode.episode_id,
        )

        first = markdown.index("b_001")
        second = markdown.index("b_002")
        third = markdown.index("b_003")
        self.assertLess(first, second)
        self.assertLess(second, third)


if __name__ == "__main__":
    unittest.main()
