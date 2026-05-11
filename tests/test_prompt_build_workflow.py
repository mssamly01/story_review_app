import unittest

from app.services.beat_generator_service import BeatGeneratorService
from app.services.episode_planner_service import EpisodePlannerService
from app.services.project_service import ProjectService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.review_rewriter_service import ReviewRewriterService


class PromptBuildWorkflowTests(unittest.TestCase):
    def test_phase_7_builds_prompts_after_review_rewrite(self) -> None:
        project_service = ProjectService()
        planner = EpisodePlannerService(project_service)
        beat_generator = BeatGeneratorService(project_service)
        rewriter = ReviewRewriterService()
        prompt_builder = PromptBuilderService()
        project = project_service.create_project(
            "Căn nhà cũ",
            default_art_style="dark fantasy webtoon",
        )
        chapter = project_service.add_source_chapter(
            project,
            title="Chương 1",
            chapter_number=1,
            raw_text="Lâm Vũ trở về căn nhà cũ và nghe tiếng động trong đêm.",
        )
        raw_text = chapter.raw_text
        project_service.add_character(
            project,
            character_id="Lâm Vũ",
            name="Lâm Vũ",
            visual_prompt_base=(
                "young man, messy black hair, gray eyes, black jacket, white shirt"
            ),
        )
        project_service.add_location(
            project,
            location_id="căn nhà cũ",
            name="Căn nhà cũ",
            visual_prompt_base="old countryside house, dusty walls, dim moonlight",
        )
        project_service.add_style_preset(
            project,
            style_id="dark_fantasy_webtoon",
            name="Dark Fantasy Webtoon",
            positive_prompt="dark fantasy webtoon style, cinematic lighting",
            negative_prompt="flat lighting, watermark, text",
        )
        episode = planner.plan_episode(
            project,
            selected_source_chapter_ids=[chapter.chapter_id],
            narration_style="mysterious",
            retelling_density="full",
        )
        beats = beat_generator.generate_beats_for_episode(
            project,
            episode.episode_id,
            retelling_density="condensed",
        )
        rewriter.rewrite_episode(project, episode.episode_id)
        review_texts = {beat.beat_id: beat.review_text for beat in beats}

        prompted_beats = prompt_builder.build_prompts_for_episode(
            project,
            episode.episode_id,
        )

        self.assertEqual(prompted_beats, beats)
        self.assertTrue(all(beat.image_prompt for beat in prompted_beats))
        self.assertTrue(all(beat.negative_prompt for beat in prompted_beats))
        for beat in prompted_beats:
            self.assertEqual(beat.review_text, review_texts[beat.beat_id])
        self.assertEqual(chapter.raw_text, raw_text)


if __name__ == "__main__":
    unittest.main()
