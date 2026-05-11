import os
import unittest
from unittest.mock import patch

from app.infrastructure.mock_ai_gateway import MockAIGateway
from app.services.beat_generator_service import BeatGeneratorService
from app.services.episode_planner_service import EpisodePlannerService
from app.services.export_service import ExportService
from app.services.project_service import ProjectService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.review_rewriter_service import ReviewRewriterService
from app.services.story_parser_service import StoryParserService


def build_base_project():
    project_service = ProjectService()
    project = project_service.create_project(
        "Old House Review",
        default_art_style="dark fantasy webtoon",
        retelling_density="full",
    )
    chapter = project_service.add_source_chapter(
        project,
        chapter_id="ch_001",
        title="Chapter 1",
        chapter_number=1,
        raw_text=("Lan returns to the old house. She finds a small clue on the " "dusty floor."),
    )
    project_service.add_character(
        project,
        character_id="mock_protagonist",
        name="Mock Protagonist",
        visual_prompt_base="young investigator, black coat, silver flashlight",
    )
    project_service.add_location(
        project,
        location_id="mock_location",
        name="Mock Location",
        visual_prompt_base="dusty old hallway, wooden floor, cold moonlight",
    )
    project_service.add_style_preset(
        project,
        style_id="dark_fantasy_webtoon",
        name="Dark Fantasy Webtoon",
        positive_prompt="dark fantasy webtoon style, cinematic lighting",
        negative_prompt="low quality, text, watermark, logo",
    )
    return project_service, project, chapter


class AIBackedServicesWorkflowTests(unittest.TestCase):
    def test_services_default_to_deterministic_without_ai(self) -> None:
        project_service, project, chapter = build_base_project()

        parsed = StoryParserService().parse(chapter)
        episode = EpisodePlannerService(project_service).plan_episode(
            project,
            selected_source_chapter_ids=[chapter.chapter_id],
            narration_style="mysterious",
            retelling_density="condensed",
        )
        beats = BeatGeneratorService(project_service).generate_beats_for_episode(
            project,
            episode.episode_id,
        )
        rewritten = ReviewRewriterService().rewrite_episode(
            project,
            episode.episode_id,
        )
        prompted = PromptBuilderService().build_prompts_for_episode(
            project,
            episode.episode_id,
        )

        self.assertEqual(parsed.chapter_id, chapter.chapter_id)
        self.assertGreaterEqual(len(episode.scenes), 1)
        self.assertGreaterEqual(len(beats), 1)
        self.assertTrue(all(beat.review_text for beat in rewritten))
        self.assertTrue(all(beat.image_prompt for beat in prompted))
        self.assertTrue(all(beat.negative_prompt for beat in prompted))

    def test_story_parser_can_use_mock_ai_gateway(self) -> None:
        _, _, chapter = build_base_project()
        raw_text = chapter.raw_text
        parser = StoryParserService(ai_gateway=MockAIGateway(), use_ai=True)

        parsed = parser.parse(chapter)

        self.assertEqual(chapter.raw_text, raw_text)
        self.assertEqual(parsed.chapter_id, chapter.chapter_id)
        self.assertTrue(parsed.detected_characters)
        self.assertTrue(parsed.detected_locations)
        self.assertTrue(parsed.scene_candidates)
        self.assertTrue(parsed.important_events)

    def test_episode_planner_can_use_mock_ai_gateway(self) -> None:
        project_service, project, chapter = build_base_project()
        planner = EpisodePlannerService(
            project_service,
            ai_gateway=MockAIGateway(),
            use_ai=True,
        )

        episode = planner.plan_episode(
            project,
            selected_source_chapter_ids=[chapter.chapter_id],
            narration_style="mysterious",
            retelling_density="full",
        )

        self.assertIn(episode, project.review_episodes)
        self.assertEqual(episode.source_chapter_ids, [chapter.chapter_id])
        self.assertEqual(episode.title, "Mock Review Episode")
        self.assertTrue(episode.scenes)
        self.assertEqual(episode.scenes[0].title, "Mock discovery")

    def test_beat_generator_can_use_mock_ai_gateway(self) -> None:
        project_service, project, chapter = build_base_project()
        episode = project_service.add_review_episode(
            project,
            title="Manual episode",
            source_chapter_ids=[chapter.chapter_id],
        )
        scene = project_service.add_scene(
            project,
            episode_id=episode.episode_id,
            title="Manual scene",
            summary="The lead character notices a clue.",
            characters=["mock_protagonist"],
            location="mock_location",
            mood="tense",
        )
        generator = BeatGeneratorService(
            project_service,
            ai_gateway=MockAIGateway(),
            use_ai=True,
        )

        beats = generator.generate_beats_for_scene(
            project,
            episode.episode_id,
            scene.scene_id,
        )

        self.assertEqual(scene.beats, beats)
        self.assertTrue(beats)
        for beat in beats:
            self.assertEqual(beat.scene_id, scene.scene_id)
            self.assertTrue(beat.action)
            self.assertTrue(beat.emotion)
            self.assertTrue(beat.shot_type)
            self.assertTrue(beat.visual_description)
            self.assertTrue(beat.continuity_tags)
            self.assertEqual(beat.review_text, "")
            self.assertEqual(beat.image_prompt, "")
            self.assertEqual(beat.negative_prompt, "")

    def test_review_rewriter_can_use_mock_ai_gateway(self) -> None:
        project_service, project, chapter = build_base_project()
        episode, beat = self._project_with_single_beat(project_service, project, chapter)
        raw_text = chapter.raw_text
        image_prompt = beat.image_prompt
        negative_prompt = beat.negative_prompt
        rewriter = ReviewRewriterService(
            ai_gateway=MockAIGateway(),
            use_ai=True,
        )

        rewritten = rewriter.rewrite_episode(project, episode.episode_id)

        self.assertEqual(chapter.raw_text, raw_text)
        self.assertEqual(rewritten, [beat])
        self.assertTrue(beat.review_text)
        self.assertEqual(beat.image_prompt, image_prompt)
        self.assertEqual(beat.negative_prompt, negative_prompt)

    def test_prompt_builder_can_use_mock_ai_gateway(self) -> None:
        project_service, project, chapter = build_base_project()
        episode, beat = self._project_with_single_beat(project_service, project, chapter)
        raw_text = chapter.raw_text
        review_text = beat.review_text
        builder = PromptBuilderService(ai_gateway=MockAIGateway(), use_ai=True)

        prompted = builder.build_prompts_for_episode(project, episode.episode_id)

        self.assertEqual(chapter.raw_text, raw_text)
        self.assertEqual(prompted, [beat])
        self.assertTrue(beat.image_prompt)
        self.assertTrue(beat.negative_prompt)
        self.assertEqual(beat.review_text, review_text)

    def test_use_ai_true_without_gateway_has_clear_behavior(self) -> None:
        _, _, chapter = build_base_project()
        parser = StoryParserService(use_ai=True)

        with self.assertRaisesRegex(ValueError, "requires an ai_gateway"):
            parser.parse(chapter)

    def test_ai_backed_pipeline_end_to_end_with_mock_gateway(self) -> None:
        project_service, project, chapter = build_base_project()
        raw_text = chapter.raw_text
        gateway = MockAIGateway()

        parsed = StoryParserService(
            ai_gateway=gateway,
            use_ai=True,
        ).parse(chapter)
        episode = EpisodePlannerService(
            project_service,
            ai_gateway=gateway,
            use_ai=True,
        ).plan_episode(
            project,
            selected_source_chapter_ids=[chapter.chapter_id],
            narration_style="mysterious",
            retelling_density="full",
        )
        beats = BeatGeneratorService(
            project_service,
            ai_gateway=gateway,
            use_ai=True,
        ).generate_beats_for_episode(project, episode.episode_id)
        ReviewRewriterService(ai_gateway=gateway, use_ai=True).rewrite_episode(
            project,
            episode.episode_id,
        )
        PromptBuilderService(ai_gateway=gateway, use_ai=True).build_prompts_for_episode(
            project,
            episode.episode_id,
        )
        export_service = ExportService(project_service)

        markdown = export_service.export_episode_markdown(project, episode.episode_id)
        json_data = export_service.export_episode_json(project, episode.episode_id)
        csv_text = export_service.export_episode_csv(project, episode.episode_id)
        script_text = export_service.export_review_script_txt(
            project,
            episode.episode_id,
        )
        prompts_text = export_service.export_image_prompts_txt(
            project,
            episode.episode_id,
        )

        self.assertTrue(parsed.scene_candidates)
        self.assertEqual(chapter.raw_text, raw_text)
        self.assertEqual(len(project.review_episodes), 1)
        self.assertTrue(episode.scenes)
        self.assertTrue(beats)
        self.assertTrue(all(beat.review_text for beat in beats))
        self.assertTrue(all(beat.image_prompt for beat in beats))
        self.assertTrue(all(beat.negative_prompt for beat in beats))
        self.assertIn("Mock Review Episode", markdown)
        self.assertIn(beats[0].review_text, markdown)
        self.assertIn(beats[0].image_prompt, markdown)
        self.assertEqual(json_data["episode"]["episode_id"], episode.episode_id)
        self.assertIn(beats[0].beat_id, csv_text)
        self.assertIn(beats[0].review_text, script_text)
        self.assertIn(beats[0].image_prompt, prompts_text)

    def test_no_network_or_credentials_required(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            gateway = MockAIGateway()
            result = gateway.generate_json("story_parser", {"chapter_id": "ch_001"})

        self.assertEqual(result["chapter_id"], "ch_001")
        self.assertTrue(result["detected_characters"])

    def _project_with_single_beat(self, project_service, project, chapter):
        episode = project_service.add_review_episode(
            project,
            title="Prepared episode",
            source_chapter_ids=[chapter.chapter_id],
        )
        scene = project_service.add_scene(
            project,
            episode_id=episode.episode_id,
            title="Prepared scene",
            summary="The lead character notices a clue.",
            characters=["mock_protagonist"],
            location="mock_location",
            mood="tense",
        )
        beat = project_service.add_beat(
            project,
            episode_id=episode.episode_id,
            scene_id=scene.scene_id,
            beat_id="b_001",
            order_index=1,
            story_function="discovery",
            characters=["mock_protagonist"],
            location="mock_location",
            action="finds a clue on the floor",
            emotion="curious",
            shot_type="detail shot",
            review_text="Existing narration should be preserved until rewriting.",
            visual_description="a small clue lying on a dusty floor",
            image_prompt="existing image prompt",
            negative_prompt="existing negative prompt",
            continuity_tags=["mock_protagonist", "mock_location"],
        )
        return episode, beat


if __name__ == "__main__":
    unittest.main()
