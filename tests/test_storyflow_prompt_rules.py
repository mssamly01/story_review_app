from pathlib import Path
import unittest

from app.services.continuity_checker_service import ContinuityCheckerService
from app.services.project_service import ProjectService
from app.services.prompt_builder_service import PromptBuilderService


ROOT = Path(__file__).resolve().parents[1]


class StoryflowPromptRuleTests(unittest.TestCase):
    def test_prompt_builder_includes_stable_character_identity(self) -> None:
        project, beat = build_storyflow_prompt_project()

        PromptBuilderService().build_prompt_for_beat(project, beat.beat_id)

        prompt = beat.image_prompt
        self.assertIn("narrow scar across left eyebrow", prompt)
        self.assertIn("messy black hair", prompt)
        self.assertIn("gray eyes", prompt)
        self.assertIn("slim build", prompt)
        self.assertIn("worn black jacket", prompt)
        self.assertIn("small brass compass", prompt)
        self.assertIn("muted black and silver palette", prompt)
        self.assertIn("wearing black jacket and white shirt", prompt)

    def test_prompt_builder_includes_full_location_profile(self) -> None:
        project, beat = build_storyflow_prompt_project()

        PromptBuilderService().build_prompt_for_beat(project, beat.beat_id)

        prompt = beat.image_prompt
        self.assertIn("old narrow hallway with dusty wooden floor", prompt)
        self.assertIn("countryside wooden house hallway", prompt)
        self.assertIn("decaying residence interior", prompt)
        self.assertIn("old countryside wooden house", prompt)
        self.assertIn("rusted chain", prompt)
        self.assertIn("cold blue moonlight", prompt)
        self.assertIn("eerie and silent", prompt)
        self.assertIn("cold blue, gray, dark brown", prompt)

    def test_prompt_builder_negative_prompt_has_text_branding_guards(self) -> None:
        project, beat = build_storyflow_prompt_project()

        PromptBuilderService().build_prompt_for_beat(project, beat.beat_id)

        negative = beat.negative_prompt
        for term in [
            "low quality",
            "blurry",
            "bad anatomy",
            "text",
            "caption",
            "subtitles",
            "speech bubble",
            "watermark",
            "logo",
        ]:
            self.assertIn(term, negative)

    def test_prompt_builder_sanitizes_forbidden_positive_text_requests(self) -> None:
        project, beat = build_storyflow_prompt_project()
        style = project.style_presets[0]
        style.positive_prompt = (
            "dark fantasy webtoon style, visible text, logo, subtitles, "
            "speech bubble, caption, cinematic lighting"
        )

        PromptBuilderService().build_prompt_for_beat(project, beat.beat_id)

        lowered_prompt = beat.image_prompt.lower()
        for blocked in [
            "visible text",
            "logo",
            "subtitles",
            "speech bubble",
            "caption",
        ]:
            self.assertNotIn(blocked, lowered_prompt)
        self.assertIn("cinematic lighting", beat.image_prompt)
        self.assertIn("speech bubble", beat.negative_prompt)

    def test_continuity_detects_missing_stable_character_identity(self) -> None:
        project, beat = build_storyflow_prompt_project()
        beat.image_prompt = (
            "dark fantasy webtoon style, Lam Vu wearing black jacket and white shirt, "
            "old narrow hallway with dusty wooden floor, cold blue moonlight, "
            "discovers fresh footprints, suspicious expression, low angle close-up"
        )
        beat.negative_prompt = (
            "low quality, blurry, text, watermark, logo, captions, subtitles, speech bubble"
        )

        issues = ContinuityCheckerService().check_beat(project, beat.beat_id)

        self.assertIn("prompt_missing_character_detail", {issue.category for issue in issues})

    def test_prompt_templates_include_story_review_consistency_rules(self) -> None:
        prompt_paths = [
            ROOT / "app" / "prompts" / "image_prompt_builder_prompt.md",
            ROOT / "app" / "prompts" / "continuity_checker_prompt.md",
            ROOT / "app" / "prompts" / "beat_package_generator_prompt.md",
        ]

        for path in prompt_paths:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8").lower()
                self.assertIn("visual_prompt_base", text)
                self.assertIn("same as above", text)
                self.assertIn("default outfit", text)
                self.assertIn("speech bubble", text)
                self.assertIn("negative_prompt", text)


def build_storyflow_prompt_project():
    project_service = ProjectService()
    project = project_service.create_project(
        "Storyflow Prompt Rules",
        default_art_style="dark_fantasy_webtoon",
    )
    chapter = project_service.add_source_chapter(
        project,
        title="Chapter 1",
        chapter_number=1,
        raw_text="Lam Vu finds fresh footprints in the old hallway.",
    )
    project_service.add_character(
        project,
        character_id="lam_vu",
        name="Lam Vu",
        visual_prompt_base="Lam Vu",
        face_details="narrow scar across left eyebrow",
        hair="messy black hair",
        eyes="gray eyes",
        body_type="slim build",
        default_outfit="black jacket and white shirt",
        wardrobe_details="worn black jacket with silver zipper",
        prop_details="small brass compass",
        color_palette="muted black and silver palette",
        continuity_tags=["scar", "black jacket", "brass compass"],
        negative_prompt_terms=["different hairstyle", "wrong outfit"],
    )
    project_service.add_location(
        project,
        location_id="old_house_hallway",
        name="Old House Hallway",
        location_type="decaying residence interior",
        description="countryside wooden house hallway",
        mood="eerie and silent",
        lighting="cold blue moonlight through broken windows",
        color_palette="cold blue, gray, dark brown",
        architecture_style="old countryside wooden house",
        recurring_props=["rusted chain", "dusty floor", "cracked walls"],
        visual_prompt_base="old narrow hallway with dusty wooden floor",
        continuity_tags=["locked door", "dusty floor"],
        negative_prompt_terms=["modern hallway"],
    )
    project_service.add_style_preset(
        project,
        style_id="dark_fantasy_webtoon",
        name="Dark Fantasy Webtoon",
        positive_prompt="dark fantasy webtoon style, cinematic lighting, dramatic shadows",
        negative_prompt="low quality, blurry, bad anatomy",
        lighting_style="moonlight, rim light",
        color_palette="deep blue and black",
        forbidden_terms=["watermark", "logo", "text overlay", "speech bubble"],
    )
    episode = project_service.add_review_episode(
        project,
        title="Episode 1",
        source_chapter_ids=[chapter.chapter_id],
        episode_id="ep_001",
    )
    scene = project_service.add_scene(
        project,
        episode_id=episode.episode_id,
        title="Footprints",
        characters=["lam_vu"],
        location="old_house_hallway",
        mood="suspicious",
    )
    beat = project_service.add_beat(
        project,
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        beat_id="beat_001",
        order_index=1,
        characters=["lam_vu"],
        location="old_house_hallway",
        action="discovers fresh footprints near the locked door",
        emotion="suspicious",
        shot_type="low angle close-up",
        visual_description="fresh footprints cutting across the dusty floor",
        review_text="Lam Vu suddenly notices fresh footprints across the dusty floor.",
        continuity_tags=["lam_vu", "old_house_hallway", "locked door"],
    )
    return project, beat


if __name__ == "__main__":
    unittest.main()
