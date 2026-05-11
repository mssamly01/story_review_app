"""Generation workflow controller for the UI."""

from __future__ import annotations

from app.domain.beat import Beat
from app.domain.episode import ReviewEpisode
from app.domain.project import Project
from app.domain.scene import Scene
from app.infrastructure.ai_gateway import AIGateway
from app.infrastructure.ai_gateway_factory import create_ai_gateway
from app.services.beat_generator_service import BeatGeneratorService
from app.services.episode_planner_service import EpisodePlannerService
from app.services.project_service import ProjectService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.review_rewriter_service import ReviewRewriterService
from app.services.story_parser_service import ParsedChapterResult, StoryParserService


class GenerationController:
    def __init__(self, project_service: ProjectService | None = None) -> None:
        self.project_service = project_service or ProjectService()

    def parse_story(
        self,
        project: Project,
        chapter_id: str,
        *,
        ai_mode: str = "deterministic",
        model: str | None = None,
    ) -> ParsedChapterResult:
        chapter = self._find_chapter(project, chapter_id)
        gateway = self._gateway_for_mode(ai_mode, model)
        return StoryParserService(
            ai_gateway=gateway,
            use_ai=gateway is not None,
        ).parse(chapter)

    def plan_episode(
        self,
        project: Project,
        *,
        chapter_id: str,
        episode_title: str,
        tone: str = "mysterious",
        density: str = "full",
        ai_mode: str = "deterministic",
        model: str | None = None,
    ) -> ReviewEpisode:
        gateway = self._gateway_for_mode(ai_mode, model)
        return EpisodePlannerService(
            self.project_service,
            ai_gateway=gateway,
            use_ai=gateway is not None,
        ).plan_episode(
            project,
            selected_source_chapter_ids=[chapter_id],
            narration_style=tone,
            retelling_density=density,
            episode_title=episode_title,
        )

    def generate_beats(
        self,
        project: Project,
        episode_id: str,
        *,
        density: str | None = None,
        ai_mode: str = "deterministic",
        model: str | None = None,
    ) -> list[Beat]:
        gateway = self._gateway_for_mode(ai_mode, model)
        return BeatGeneratorService(
            self.project_service,
            ai_gateway=gateway,
            use_ai=gateway is not None,
        ).generate_beats_for_episode(
            project,
            episode_id,
            retelling_density=density,
        )

    def rewrite_review(
        self,
        project: Project,
        episode_id: str,
        *,
        tone: str | None = None,
        density: str | None = None,
        ai_mode: str = "deterministic",
        model: str | None = None,
    ) -> list[Beat]:
        gateway = self._gateway_for_mode(ai_mode, model)
        return ReviewRewriterService(
            ai_gateway=gateway,
            use_ai=gateway is not None,
        ).rewrite_episode(
            project,
            episode_id,
            narration_style=tone,
            retelling_density=density,
        )

    def build_prompts(
        self,
        project: Project,
        episode_id: str,
        *,
        style_preset_id: str | None = None,
        ai_mode: str = "deterministic",
        model: str | None = None,
    ) -> list[Beat]:
        gateway = self._gateway_for_mode(ai_mode, model)
        return PromptBuilderService(
            ai_gateway=gateway,
            use_ai=gateway is not None,
        ).build_prompts_for_episode(
            project,
            episode_id,
            style_preset_id=style_preset_id,
        )

    def generate_beat_package(
        self,
        project: Project,
        episode_id: str,
        *,
        scene_id: str | None = None,
        tone: str | None = None,
        density: str | None = None,
        style_preset_id: str | None = None,
        ai_mode: str = "deterministic",
        model: str | None = None,
    ) -> list[Beat]:
        gateway = self._gateway_for_mode(ai_mode, model)
        service = BeatGeneratorService(
            project_service=self.project_service,
            ai_gateway=gateway,
        )
        if scene_id:
            return service.generate_unified_package_for_scene(
                project,
                episode_id,
                scene_id,
                narration_style=tone,
                retelling_density=density,
                style_preset_id=style_preset_id,
                use_ai=gateway is not None,
            )
        return service.generate_unified_package_for_episode(
            project,
            episode_id,
            narration_style=tone,
            retelling_density=density,
            style_preset_id=style_preset_id,
            use_ai=gateway is not None,
        )

    def run_full_pipeline(
        self,
        project: Project,
        *,
        chapter_id: str,
        episode_title: str,
        tone: str = "mysterious",
        density: str = "full",
        style_preset_id: str | None = None,
        ai_mode: str = "deterministic",
        model: str | None = None,
    ) -> ReviewEpisode:
        self.parse_story(project, chapter_id, ai_mode=ai_mode, model=model)
        episode = self.plan_episode(
            project,
            chapter_id=chapter_id,
            episode_title=episode_title,
            tone=tone,
            density=density,
            ai_mode=ai_mode,
            model=model,
        )
        self.generate_beats(
            project,
            episode.episode_id,
            density=density,
            ai_mode=ai_mode,
            model=model,
        )
        self.rewrite_review(
            project,
            episode.episode_id,
            tone=tone,
            density=density,
            ai_mode=ai_mode,
            model=model,
        )
        self.build_prompts(
            project,
            episode.episode_id,
            style_preset_id=style_preset_id,
            ai_mode=ai_mode,
            model=model,
        )
        return episode

    def update_beat_fields(self, beat: Beat, **fields: object) -> Beat:
        list_fields = {"characters", "continuity_tags"}
        for name, value in fields.items():
            if value is None or not hasattr(beat, name):
                continue
            if name in list_fields and isinstance(value, str):
                setattr(beat, name, self._split_list_text(value))
            else:
                setattr(beat, name, value)
        return beat

    def find_episode(self, project: Project, episode_id: str) -> ReviewEpisode:
        return self.project_service.find_episode(project, episode_id)

    def find_scene(
        self, project: Project, episode_id: str, scene_id: str
    ) -> Scene:
        return self.project_service.find_scene(project, episode_id, scene_id)

    def _find_chapter(self, project: Project, chapter_id: str):
        for chapter in project.source_chapters:
            if chapter.chapter_id == chapter_id:
                return chapter
        raise LookupError(f"SourceChapter not found: {chapter_id}")

    def _gateway_for_mode(
        self, ai_mode: str, model: str | None
    ) -> AIGateway | None:
        if ai_mode == "deterministic":
            return None
        if ai_mode == "mock":
            return create_ai_gateway(True, mock_ai=True, model=model)
        if ai_mode == "real":
            return create_ai_gateway(True, real_ai=True, model=model)
        raise ValueError(f"Unsupported AI mode: {ai_mode}")

    def _split_list_text(self, value: str) -> list[str]:
        return [part.strip() for part in value.split(",") if part.strip()]

