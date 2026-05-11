import unittest

from app.domain.character import Character
from app.domain.location import Location
from app.domain.style_preset import StylePreset
from app.services.bible_service import BibleService
from app.services.project_service import ProjectService
from app.services.prompt_builder_service import PromptBuilderService


class AdvancedPromptBuilderTests(unittest.TestCase):
    def test_prompt_builder_uses_advanced_character_fields(self) -> None:
        project, beat = build_prompt_ready_project()

        PromptBuilderService().build_prompt_for_beat(
            project,
            beat.beat_id,
            style_preset_id="advanced_style",
        )

        self.assertIn(
            "young detective with silver eyes",
            beat.image_prompt,
        )
        self.assertIn("navy coat with brass buttons", beat.image_prompt)
        self.assertIn("wrong coat", beat.negative_prompt)

    def test_prompt_builder_uses_advanced_location_fields(self) -> None:
        project, beat = build_prompt_ready_project()

        PromptBuilderService().build_prompt_for_beat(
            project,
            beat.beat_id,
            style_preset_id="advanced_style",
        )

        self.assertIn("old archive room, tall shelves", beat.image_prompt)
        self.assertIn("green desk lamp", beat.image_prompt)
        self.assertIn("dusty", beat.image_prompt)
        self.assertIn("red sealed envelope", beat.image_prompt)
        self.assertIn("modern office chair", beat.negative_prompt)

    def test_prompt_builder_uses_advanced_style_preset(self) -> None:
        project, beat = build_prompt_ready_project()

        PromptBuilderService().build_prompt_for_beat(
            project,
            beat.beat_id,
            style_preset_id="advanced_style",
        )

        self.assertIn("noir detective comic style", beat.image_prompt)
        self.assertIn("black, gray, amber", beat.image_prompt)
        self.assertIn("streetlamp glow", beat.image_prompt)
        self.assertIn("low contrast", beat.negative_prompt)
        self.assertIn("captions", beat.negative_prompt)

    def test_prompt_builder_does_not_modify_review_text_or_raw_text(self) -> None:
        project, beat = build_prompt_ready_project()
        review_text = beat.review_text
        raw_text = project.source_chapters[0].raw_text

        PromptBuilderService().build_prompt_for_beat(
            project,
            beat.beat_id,
            style_preset_id="advanced_style",
        )

        self.assertEqual(beat.review_text, review_text)
        self.assertEqual(project.source_chapters[0].raw_text, raw_text)


def build_prompt_ready_project():
    project_service = ProjectService()
    project = project_service.create_project(
        "Prompt Story",
        default_art_style="advanced_style",
    )
    chapter = project_service.add_source_chapter(
        project,
        title="Chapter 1",
        chapter_number=1,
        raw_text="Lan finds a sealed envelope in the old archive.",
    )
    BibleService().add_or_update_character(
        project,
        Character(
            character_id="lan",
            name="Lan",
            appearance="focused expression",
            hair="short black hair",
            eyes="silver eyes",
            default_outfit="navy coat with brass buttons",
            visual_prompt_base="young detective with silver eyes",
            negative_prompt_terms=["wrong coat"],
        ),
    )
    BibleService().add_or_update_location(
        project,
        Location(
            location_id="archive",
            name="Archive",
            mood="dusty",
            lighting="green desk lamp",
            recurring_props=["red sealed envelope"],
            visual_prompt_base="old archive room, tall shelves",
            negative_prompt_terms=["modern office chair"],
        ),
    )
    BibleService().add_or_update_style_preset(
        project,
        StylePreset(
            style_id="advanced_style",
            name="Advanced Style",
            positive_prompt="noir detective comic style",
            negative_prompt="low contrast",
            color_palette="black, gray, amber",
            lighting_style="streetlamp glow",
            forbidden_terms=["captions"],
        ),
    )
    episode = project_service.add_review_episode(
        project,
        title="Episode 1",
        source_chapter_ids=[chapter.chapter_id],
    )
    scene = project_service.add_scene(
        project,
        episode_id=episode.episode_id,
        title="Archive clue",
        summary="Lan studies the hidden envelope.",
        characters=["lan"],
        location="archive",
        mood="suspicious",
    )
    beat = project_service.add_beat(
        project,
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        beat_id="b_001",
        story_function="discovery",
        characters=["lan"],
        location="archive",
        action="Lan opens the red sealed envelope",
        emotion="curious",
        shot_type="detail shot",
        review_text="Lan slows down and studies the envelope.",
        visual_description="Lan holds the old envelope under the lamp.",
    )
    return project, beat


if __name__ == "__main__":
    unittest.main()
