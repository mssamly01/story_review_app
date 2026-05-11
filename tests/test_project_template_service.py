import unittest

from app.domain.style_preset import StylePreset
from app.services.beat_generator_service import BeatGeneratorService
from app.services.episode_planner_service import EpisodePlannerService
from app.services.project_service import ProjectService
from app.services.project_template_service import ProjectTemplateService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.quality.validation import ProjectValidationService
from app.services.review_rewriter_service import ReviewRewriterService

REQUIRED_TEMPLATE_IDS = {
    "dark_fantasy_webtoon",
    "korean_romance_webtoon",
    "horror_webtoon",
    "action_manhwa",
    "historical_fantasy_manhua",
    "modern_school_webtoon",
    "noir_detective_comic",
    "soft_watercolor_webtoon",
}


class ProjectTemplateServiceTests(unittest.TestCase):
    def test_list_templates_contains_required_templates(self) -> None:
        templates = ProjectTemplateService().list_templates()

        self.assertEqual(
            {template.template_id for template in templates},
            REQUIRED_TEMPLATE_IDS,
        )

    def test_get_template_returns_template(self) -> None:
        template = ProjectTemplateService().get_template("dark_fantasy_webtoon")

        self.assertEqual(template.name, "Dark Fantasy Webtoon")
        self.assertEqual(template.genre, "dark fantasy")
        self.assertTrue(template.default_narration_style)
        self.assertTrue(template.default_retelling_density)

    def test_create_project_from_template(self) -> None:
        project = ProjectTemplateService().create_project_from_template(
            "dark_fantasy_webtoon",
            "My Story",
        )

        self.assertEqual(project.title, "My Story")
        self.assertEqual(project.genre, "dark fantasy")
        self.assertEqual(project.default_narration_style, "mysterious")
        self.assertEqual(project.default_art_style, "dark_fantasy_webtoon")
        self.assertTrue(project.style_presets)
        self.assertEqual(project.source_chapters, [])

    def test_create_project_from_template_no_ai_required(self) -> None:
        project = ProjectTemplateService().create_project_from_template(
            "horror_webtoon",
            "Offline Story",
        )

        self.assertEqual(project.title, "Offline Story")
        self.assertEqual(project.default_art_style, "horror_webtoon")

    def test_apply_template_to_existing_project_preserves_data(self) -> None:
        project_service = ProjectService()
        project = project_service.create_project("Existing")
        chapter = project_service.add_source_chapter(
            project,
            title="Chapter 1",
            chapter_number=1,
            raw_text="Original raw text stays exactly here.",
        )
        episode = project_service.add_review_episode(
            project,
            title="Episode 1",
            source_chapter_ids=[chapter.chapter_id],
        )
        scene = project_service.add_scene(
            project,
            episode_id=episode.episode_id,
            title="Scene 1",
        )
        beat = project_service.add_beat(
            project,
            episode_id=episode.episode_id,
            scene_id=scene.scene_id,
            beat_id="b_001",
            order_index=1,
        )
        raw_text = chapter.raw_text

        ProjectTemplateService(project_service).apply_template_to_project(
            project,
            "dark_fantasy_webtoon",
        )

        self.assertEqual(project.source_chapters[0].chapter_id, chapter.chapter_id)
        self.assertEqual(project.review_episodes[0].episode_id, episode.episode_id)
        self.assertEqual(project.review_episodes[0].scenes[0].scene_id, scene.scene_id)
        self.assertEqual(project.review_episodes[0].scenes[0].beats[0].beat_id, beat.beat_id)
        self.assertEqual(project.source_chapters[0].raw_text, raw_text)

    def test_apply_template_is_idempotent(self) -> None:
        project = ProjectService().create_project("Existing")
        service = ProjectTemplateService()

        service.apply_template_to_project(project, "dark_fantasy_webtoon")
        service.apply_template_to_project(project, "dark_fantasy_webtoon")

        style_ids = [style.style_id for style in project.style_presets]
        self.assertEqual(style_ids.count("dark_fantasy_webtoon"), 1)

    def test_apply_template_does_not_overwrite_existing_styles_by_default(self) -> None:
        project = ProjectService().create_project("Existing")
        project.style_presets.append(
            StylePreset(
                style_id="dark_fantasy_webtoon",
                name="Custom Dark",
                positive_prompt="custom positive prompt",
            )
        )

        ProjectTemplateService().apply_template_to_project(
            project,
            "dark_fantasy_webtoon",
        )

        self.assertEqual(project.style_presets[0].positive_prompt, "custom positive prompt")

    def test_apply_template_can_overwrite_styles_when_requested(self) -> None:
        project = ProjectService().create_project("Existing")
        project.style_presets.append(
            StylePreset(
                style_id="dark_fantasy_webtoon",
                name="Custom Dark",
                positive_prompt="custom positive prompt",
            )
        )

        ProjectTemplateService().apply_template_to_project(
            project,
            "dark_fantasy_webtoon",
            overwrite_existing_styles=True,
        )

        self.assertIn("dark fantasy webtoon style", project.style_presets[0].positive_prompt)

    def test_template_project_passes_validation_or_has_no_errors(self) -> None:
        project = ProjectTemplateService().create_project_from_template(
            "dark_fantasy_webtoon",
            "Template Story",
        )

        issues = ProjectValidationService().validate_project(project)

        self.assertFalse([issue for issue in issues if issue.severity == "error"])

    def test_template_project_works_with_existing_pipeline(self) -> None:
        project_service = ProjectService()
        project = ProjectTemplateService(project_service).create_project_from_template(
            "dark_fantasy_webtoon",
            "Pipeline Story",
        )
        chapter = project_service.add_source_chapter(
            project,
            title="Chapter 1",
            chapter_number=1,
            raw_text="Lan returns to the old house. She finds a clue on the floor.",
        )
        episode = EpisodePlannerService(project_service).plan_episode(
            project,
            selected_source_chapter_ids=[chapter.chapter_id],
            narration_style=project.default_narration_style,
            retelling_density=project.retelling_density,
            episode_title="Episode 1",
        )
        BeatGeneratorService(project_service).generate_beats_for_episode(
            project,
            episode.episode_id,
        )
        ReviewRewriterService().rewrite_episode(project, episode.episode_id)
        PromptBuilderService().build_prompts_for_episode(project, episode.episode_id)

        prompts = [beat.image_prompt for scene in episode.scenes for beat in scene.beats]
        self.assertTrue(prompts)
        self.assertTrue(all("dark fantasy webtoon style" in prompt for prompt in prompts))


if __name__ == "__main__":
    unittest.main()
