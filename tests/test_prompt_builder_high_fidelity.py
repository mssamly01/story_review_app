import unittest

from app.services.project_service import ProjectService
from app.services.prompt_builder_service import PromptBuilderService


class PromptBuilderHighFidelityTests(unittest.TestCase):
    def test_bible_style_data_affects_beat_prompt(self) -> None:
        project_service = ProjectService()
        project = project_service.create_project("High Fidelity Test")

        # 1. Add Character with rich details
        project_service.add_character(
            project,
            character_id="lam_vu",
            name="Lâm Vũ",
            visual_prompt_base="young man with messy black hair and gray eyes",
            appearance="slim young man with calm but cautious expression",
            hair="messy black hair",
            eyes="gray eyes",
            body_type="slim build",
            default_outfit="black jacket and white shirt",
            negative_prompt_terms=["different hairstyle", "wrong outfit"],
        )

        # 2. Add Location with rich details
        project_service.add_location(
            project,
            location_id="old_house_hallway",
            name="Old House Hallway",
            visual_prompt_base="old narrow hallway with dusty wooden floor and old wooden doors",
            mood="eerie and mysterious",
            lighting="dim moonlight through broken windows",
            color_palette="cold blue, gray, dark brown",
            architecture_style="old countryside wooden house",
            recurring_props=["rusted chain", "dusty floor", "cracked walls"],
            negative_prompt_terms=["modern hallway", "bright daylight"],
        )

        # 3. Add StylePreset with rich details
        project_service.add_style_preset(
            project,
            style_id="dark_fantasy_webtoon",
            name="Dark Fantasy Webtoon",
            positive_prompt="dark fantasy webtoon style, cinematic lighting, dramatic shadows, detailed background",
            negative_prompt="low quality, blurry, bad anatomy",
            lighting_style="moonlight, rim light, deep shadows",
            color_palette="deep blue, black, purple",
            camera_style="cinematic close-up composition",
            mood_keywords=["mysterious", "tense", "eerie"],
            forbidden_terms=["watermark", "logo", "subtitles", "speech bubble"],
        )
        project.default_art_style = "dark_fantasy_webtoon"

        # 4. Setup Episode/Scene/Beat
        chapter = project_service.add_source_chapter(
            project, title="Ch 1", chapter_number=1, raw_text="Source text"
        )
        episode = project_service.add_review_episode(
            project, title="Ep 1", source_chapter_ids=[chapter.chapter_id]
        )
        scene = project_service.add_scene(
            project,
            episode_id=episode.episode_id,
            title="Scene 1",
            characters=["lam_vu"],
            location="old_house_hallway",
        )
        beat = project_service.add_beat(
            project,
            episode_id=episode.episode_id,
            scene_id=scene.scene_id,
            beat_id="b_001",
            order_index=1,
            characters=["lam_vu"],
            location="old_house_hallway",
            action="discovers fresh footprints",
            emotion="suspicious",
            shot_type="low angle close-up",
            visual_description="fresh footprints on dusty floor before a locked door",
        )

        # 5. Run PromptBuilder
        service = PromptBuilderService(use_ai=False)
        service.build_prompt_for_beat(project, beat.beat_id)

        p = beat.image_prompt
        n = beat.negative_prompt

        # 6. Assert Image Prompt content
        self.assertIn("dark fantasy webtoon style", p)
        self.assertIn("cinematic lighting", p)
        self.assertIn("dramatic shadows", p)
        self.assertIn("messy black hair", p)
        self.assertIn("gray eyes", p)
        self.assertIn("slim build", p)
        self.assertIn("Outfit: black jacket and white shirt", p)
        self.assertIn("old narrow hallway", p)
        self.assertIn("dusty wooden floor", p)
        self.assertIn("dim moonlight", p)
        self.assertIn("eerie and mysterious", p)
        self.assertIn("rusted chain", p)
        self.assertIn("fresh footprints", p)
        self.assertIn("suspicious", p)
        self.assertIn("low angle close-up", p)

        # 7. Assert Negative Prompt content
        self.assertIn("low quality", n)
        self.assertIn("blurry", n)
        self.assertIn("bad anatomy", n)
        self.assertIn("different hairstyle", n)
        self.assertIn("wrong outfit", n)
        self.assertIn("modern hallway", n)
        self.assertIn("bright daylight", n)
        self.assertIn("watermark", n)
        self.assertIn("logo", n)
        self.assertIn("subtitles", n)
        self.assertIn("speech bubble", n)

        # 8. Integrity check
        self.assertEqual(chapter.raw_text, "Source text")
        self.assertEqual(beat.action, "discovers fresh footprints")


if __name__ == "__main__":
    unittest.main()
