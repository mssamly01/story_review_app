"""Offline project templates and onboarding defaults."""

from __future__ import annotations

from app.domain.project import Project
from app.domain.project_template import ProjectTemplate
from app.domain.style_preset import StylePreset
from app.services.bible_service import BibleService
from app.services.project_service import ProjectService


class ProjectTemplateService:
    REQUIRED_TEMPLATE_IDS = [
        "dark_fantasy_webtoon",
        "korean_romance_webtoon",
        "horror_webtoon",
        "action_manhwa",
        "historical_fantasy_manhua",
        "modern_school_webtoon",
        "noir_detective_comic",
        "soft_watercolor_webtoon",
    ]

    def __init__(
        self,
        project_service: ProjectService | None = None,
        bible_service: BibleService | None = None,
    ) -> None:
        self.project_service = project_service or ProjectService()
        self.bible_service = bible_service or BibleService()

    def list_templates(self) -> list[ProjectTemplate]:
        return [self.get_template(template_id) for template_id in self.REQUIRED_TEMPLATE_IDS]

    def get_template(self, template_id: str) -> ProjectTemplate:
        template = self._templates_by_id().get(template_id)
        if template is None:
            raise LookupError(f"ProjectTemplate not found: {template_id}")
        return template

    def create_project_from_template(
        self,
        template_id: str,
        title: str,
        project_id: str | None = None,
        language: str | None = None,
    ) -> Project:
        template = self.get_template(template_id)
        project = self.project_service.create_project(
            title,
            project_id=project_id,
            genre=template.genre,
            language=language or template.default_language,
            default_narration_style=template.default_narration_style,
            default_art_style=template.default_art_style,
            retelling_density=template.default_retelling_density,
        )
        self.apply_template_to_project(project, template_id)
        return project

    def apply_template_to_project(
        self,
        project: Project,
        template_id: str,
        overwrite_existing_styles: bool = False,
    ) -> Project:
        template = self.get_template(template_id)
        project.genre = project.genre or template.genre
        project.language = project.language or template.default_language
        project.default_narration_style = template.default_narration_style
        project.default_art_style = template.default_art_style
        project.retelling_density = template.default_retelling_density
        self._apply_style_presets(
            project,
            template,
            overwrite_existing_styles=overwrite_existing_styles,
        )
        project.touch()
        return project

    def _apply_style_presets(
        self,
        project: Project,
        template: ProjectTemplate,
        *,
        overwrite_existing_styles: bool,
    ) -> None:
        by_id = {style.style_id: index for index, style in enumerate(project.style_presets)}
        for style in template.default_style_presets:
            style_copy = self._copy_style(style)
            existing_index = by_id.get(style.style_id)
            if existing_index is None:
                project.style_presets.append(style_copy)
                by_id[style.style_id] = len(project.style_presets) - 1
            elif overwrite_existing_styles:
                project.style_presets[existing_index] = style_copy

    def _templates_by_id(self) -> dict[str, ProjectTemplate]:
        styles_by_id = self._default_styles_by_id()
        metadata = self._template_metadata()
        templates: dict[str, ProjectTemplate] = {}
        for template_id in self.REQUIRED_TEMPLATE_IDS:
            style = styles_by_id[template_id]
            config = metadata[template_id]
            templates[template_id] = ProjectTemplate(
                template_id=template_id,
                name=config["name"],
                description=config["description"],
                genre=config["genre"],
                default_language="vi",
                default_narration_style=config["narration_style"],
                default_retelling_density=config["density"],
                default_art_style=style.style_id,
                recommended_chapters_per_episode=config["chapters_per_episode"],
                style_preset_ids=[style.style_id],
                default_style_presets=[self._copy_style(style)],
                prompt_guidelines=config["prompt_guidelines"],
                review_guidelines=config["review_guidelines"],
                character_bible_placeholders=config["character_placeholders"],
                location_bible_placeholders=config["location_placeholders"],
                export_defaults={
                    "formats": ["markdown", "json", "csv", "review-txt", "prompts-txt"],
                    "primary_format": "markdown",
                },
            )
        return templates

    def _default_styles_by_id(self) -> dict[str, StylePreset]:
        project = Project(project_id="template_styles", title="Template Styles")
        self.bible_service.create_default_style_presets(project)
        return {style.style_id: style for style in project.style_presets}

    def _template_metadata(self) -> dict[str, dict]:
        return {
            "dark_fantasy_webtoon": {
                "name": "Dark Fantasy Webtoon",
                "description": "Mysterious long-form retelling with moody fantasy illustration defaults.",
                "genre": "dark fantasy",
                "narration_style": "mysterious",
                "density": "full",
                "chapters_per_episode": 1,
                "prompt_guidelines": [
                    "Use cinematic lighting and dramatic shadows.",
                    "Keep character outfits and eerie locations consistent.",
                    "Focus each prompt on one clear beat moment.",
                ],
                "review_guidelines": [
                    "Retell suspicious details slowly and clearly.",
                    "Preserve cause and effect across scenes.",
                ],
                "character_placeholders": [
                    {"role": "protagonist", "visual_prompt_base": ""},
                    {"role": "mysterious supporting character", "visual_prompt_base": ""},
                ],
                "location_placeholders": [
                    {"location_type": "recurring eerie setting", "visual_prompt_base": ""},
                ],
            },
            "korean_romance_webtoon": {
                "name": "Korean Romance Webtoon",
                "description": "Emotion-forward romance template with clean webtoon visuals.",
                "genre": "romance",
                "narration_style": "dramatic",
                "density": "balanced",
                "chapters_per_episode": 2,
                "prompt_guidelines": [
                    "Use soft lighting, expressive faces, and warm palettes.",
                    "Keep outfits elegant and consistent between emotional beats.",
                ],
                "review_guidelines": [
                    "Retell emotional turns in a natural voice-over rhythm.",
                    "Avoid reducing relationship shifts to short summaries.",
                ],
                "character_placeholders": [
                    {"role": "romantic lead", "visual_prompt_base": ""},
                    {"role": "second lead", "visual_prompt_base": ""},
                ],
                "location_placeholders": [
                    {"location_type": "school or city meeting place", "visual_prompt_base": ""},
                ],
            },
            "horror_webtoon": {
                "name": "Horror Webtoon",
                "description": "Tense horror retelling with oppressive visual atmosphere.",
                "genre": "horror",
                "narration_style": "mysterious",
                "density": "full",
                "chapters_per_episode": 1,
                "prompt_guidelines": [
                    "Use low light, claustrophobic framing, and unsettling composition.",
                    "Keep fear beats focused on one visible threat or clue.",
                ],
                "review_guidelines": [
                    "Build dread through concrete details.",
                    "Keep reveals clear without rushing.",
                ],
                "character_placeholders": [
                    {"role": "survivor or investigator", "visual_prompt_base": ""},
                ],
                "location_placeholders": [
                    {"location_type": "haunted or dangerous place", "visual_prompt_base": ""},
                ],
            },
            "action_manhwa": {
                "name": "Action Manhwa",
                "description": "Fast, high-impact action retelling with dynamic visuals.",
                "genre": "action",
                "narration_style": "fast-paced",
                "density": "balanced",
                "chapters_per_episode": 2,
                "prompt_guidelines": [
                    "Use dynamic composition and readable action silhouettes.",
                    "Keep each beat to one clear action moment.",
                ],
                "review_guidelines": [
                    "Retell action beats clearly and directly.",
                    "Keep stakes and character decisions visible.",
                ],
                "character_placeholders": [
                    {"role": "fighter protagonist", "visual_prompt_base": ""},
                    {"role": "rival or enemy", "visual_prompt_base": ""},
                ],
                "location_placeholders": [
                    {"location_type": "arena or conflict location", "visual_prompt_base": ""},
                ],
            },
            "historical_fantasy_manhua": {
                "name": "Historical Fantasy Manhua",
                "description": "Elegant fantasy retelling with ornate historical visuals.",
                "genre": "historical fantasy",
                "narration_style": "dramatic",
                "density": "full",
                "chapters_per_episode": 1,
                "prompt_guidelines": [
                    "Use flowing outfits, ornate locations, and graceful framing.",
                    "Preserve period details and magical atmosphere.",
                ],
                "review_guidelines": [
                    "Retell political and emotional turns with enough context.",
                    "Keep names, alliances, and locations clear.",
                ],
                "character_placeholders": [
                    {"role": "noble lead", "visual_prompt_base": ""},
                    {"role": "royal or sect rival", "visual_prompt_base": ""},
                ],
                "location_placeholders": [
                    {"location_type": "palace, sect hall, or ancient city", "visual_prompt_base": ""},
                ],
            },
            "modern_school_webtoon": {
                "name": "Modern School Webtoon",
                "description": "Clean school drama setup for everyday but detailed retelling.",
                "genre": "school drama",
                "narration_style": "humorous",
                "density": "balanced",
                "chapters_per_episode": 2,
                "prompt_guidelines": [
                    "Use clean campus backgrounds and consistent uniforms.",
                    "Keep expressions readable in social scenes.",
                ],
                "review_guidelines": [
                    "Explain character choices and social tension clearly.",
                    "Keep the narration natural and easy to listen to.",
                ],
                "character_placeholders": [
                    {"role": "student lead", "visual_prompt_base": ""},
                    {"role": "classmate or rival", "visual_prompt_base": ""},
                ],
                "location_placeholders": [
                    {"location_type": "classroom or campus location", "visual_prompt_base": ""},
                ],
            },
            "noir_detective_comic": {
                "name": "Noir Detective Comic",
                "description": "Mystery template for clues, suspicion, and moody city settings.",
                "genre": "mystery",
                "narration_style": "mysterious",
                "density": "full",
                "chapters_per_episode": 1,
                "prompt_guidelines": [
                    "Use hard shadows, rain-soaked settings, and clue-focused framing.",
                    "Keep suspects, objects, and locations visually consistent.",
                ],
                "review_guidelines": [
                    "Retell clues in order so the audience can follow the case.",
                    "Do not skip small details that later matter.",
                ],
                "character_placeholders": [
                    {"role": "detective", "visual_prompt_base": ""},
                    {"role": "suspect", "visual_prompt_base": ""},
                ],
                "location_placeholders": [
                    {"location_type": "street, office, or crime scene", "visual_prompt_base": ""},
                ],
            },
            "soft_watercolor_webtoon": {
                "name": "Soft Watercolor Webtoon",
                "description": "Gentle slice-of-life template with soft emotional visuals.",
                "genre": "slice of life",
                "narration_style": "neutral",
                "density": "balanced",
                "chapters_per_episode": 2,
                "prompt_guidelines": [
                    "Use soft brush texture, airy composition, and delicate colors.",
                    "Keep quiet emotional moments visually specific.",
                ],
                "review_guidelines": [
                    "Retell small emotional changes without over-compressing.",
                    "Keep sentences calm, clear, and voice-over friendly.",
                ],
                "character_placeholders": [
                    {"role": "main character", "visual_prompt_base": ""},
                ],
                "location_placeholders": [
                    {"location_type": "home, cafe, or quiet outdoor place", "visual_prompt_base": ""},
                ],
            },
        }

    def _copy_style(self, style: StylePreset) -> StylePreset:
        return StylePreset.from_dict(style.to_dict())
