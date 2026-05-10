"""Mock review episode planner.

The planner turns selected SourceChapter objects into a ReviewEpisode with
Scene shells. It prepares the episode -> scene -> beat pipeline but does not
generate beats or rewritten review text yet.
"""

from __future__ import annotations

from app.domain.episode import ReviewEpisode
from app.domain.project import Project
from app.domain.scene import Scene
from app.domain.source_chapter import SourceChapter
from app.services.project_service import ProjectService
from app.services.story_parser_service import (
    ImportantEvent,
    ParsedChapterResult,
    SceneCandidate,
    StoryParserService,
)


class EpisodePlannerService:
    _allowed_narration_styles = {
        "neutral",
        "dramatic",
        "mysterious",
        "humorous",
        "fast-paced",
    }
    _allowed_retelling_densities = {"full", "balanced", "condensed"}
    _base_target_beats_by_density = {
        "full": 5,
        "balanced": 4,
        "condensed": 3,
    }

    def __init__(
        self,
        project_service: ProjectService | None = None,
        story_parser_service: StoryParserService | None = None,
    ) -> None:
        self.project_service = project_service or ProjectService()
        self.story_parser_service = story_parser_service or StoryParserService()

    def plan_episode(
        self,
        project: Project,
        *,
        selected_source_chapter_ids: list[str],
        narration_style: str,
        retelling_density: str,
        episode_title: str | None = None,
    ) -> ReviewEpisode:
        self._validate_plan_request(
            selected_source_chapter_ids=selected_source_chapter_ids,
            narration_style=narration_style,
            retelling_density=retelling_density,
        )
        source_chapters = self._find_source_chapters(
            project, selected_source_chapter_ids
        )
        parsed_results = [
            self.story_parser_service.parse(source_chapter)
            for source_chapter in source_chapters
        ]
        title = episode_title or self._build_episode_title(source_chapters)

        episode = self.project_service.add_review_episode(
            project,
            title=title,
            source_chapter_ids=list(selected_source_chapter_ids),
            tone=narration_style,
            density=retelling_density,
            status="planned",
            summary=self._build_episode_summary(parsed_results),
            hook=self._build_hook(parsed_results, title),
            cliffhanger=self._build_cliffhanger(parsed_results),
        )

        for source_chapter, parsed_result in zip(source_chapters, parsed_results):
            planned_scenes = self._create_scenes_from_parsed_result(
                project=project,
                episode=episode,
                source_chapter=source_chapter,
                parsed_result=parsed_result,
                retelling_density=retelling_density,
            )
            source_chapter.parsed_scene_ids.extend(
                scene.scene_id for scene in planned_scenes
            )

        project.touch()
        return episode

    def _create_scenes_from_parsed_result(
        self,
        *,
        project: Project,
        episode: ReviewEpisode,
        source_chapter: SourceChapter,
        parsed_result: ParsedChapterResult,
        retelling_density: str,
    ) -> list[Scene]:
        scene_candidates = parsed_result.scene_candidates
        if not scene_candidates and source_chapter.raw_text.strip():
            scene_candidates = [
                SceneCandidate(
                    scene_id="sc_001",
                    title=source_chapter.title,
                    summary=source_chapter.raw_text.strip(),
                    mood="neutral",
                    importance="medium",
                )
            ]

        planned_scenes: list[Scene] = []
        for scene_candidate in scene_candidates:
            target_beats = self._target_beats_for_scene(
                scene_candidate=scene_candidate,
                retelling_density=retelling_density,
            )
            scene = self.project_service.add_scene(
                project,
                episode_id=episode.episode_id,
                title=scene_candidate.title,
                summary=self._build_scene_summary(
                    source_chapter=source_chapter,
                    parsed_result=parsed_result,
                    scene_candidate=scene_candidate,
                    target_beats=target_beats,
                ),
                characters=scene_candidate.characters,
                location=scene_candidate.location,
                mood=scene_candidate.mood,
                importance=scene_candidate.importance,
                target_beats=target_beats,
            )
            planned_scenes.append(scene)

        return planned_scenes

    def _target_beats_for_scene(
        self, *, scene_candidate: SceneCandidate, retelling_density: str
    ) -> int:
        base_count = self._base_target_beats_by_density[retelling_density]
        event_count = len(scene_candidate.important_events)
        importance_bonus = 2 if scene_candidate.importance == "high" else 1
        return base_count + importance_bonus + min(event_count, 3)

    def _build_episode_title(self, source_chapters: list[SourceChapter]) -> str:
        if len(source_chapters) == 1:
            return f"Review: {source_chapters[0].title}"
        first_title = source_chapters[0].title
        last_title = source_chapters[-1].title
        return f"Review: {first_title} - {last_title}"

    def _build_episode_summary(
        self, parsed_results: list[ParsedChapterResult]
    ) -> str:
        scene_count = sum(len(result.scene_candidates) for result in parsed_results)
        event_count = sum(len(result.important_events) for result in parsed_results)
        return (
            "Mock episode plan for detailed retelling. "
            f"Preserve {scene_count} scene candidates and {event_count} "
            "important events before beat generation."
        )

    def _build_hook(
        self, parsed_results: list[ParsedChapterResult], title: str
    ) -> str:
        first_event = self._first_important_event(parsed_results)
        if first_event:
            return f"{first_event.summary}"
        return f"{title} begins with a scene that should be retold in detail."

    def _build_cliffhanger(
        self, parsed_results: list[ParsedChapterResult]
    ) -> str:
        last_event = self._last_important_event(parsed_results)
        if last_event:
            return f"Continue from this unresolved moment: {last_event.summary}"
        return "Continue into the next scene without compressing the story flow."

    def _build_scene_summary(
        self,
        *,
        source_chapter: SourceChapter,
        parsed_result: ParsedChapterResult,
        scene_candidate: SceneCandidate,
        target_beats: int,
    ) -> str:
        related_events = [
            event.summary
            for event in parsed_result.important_events
            if event.event_id in scene_candidate.important_events
        ]
        lines = [
            f"Source: {source_chapter.chapter_id} - {source_chapter.title}.",
            scene_candidate.summary,
            (
                "Planning note: retell this scene in detail and later split it "
                f"into about {target_beats} visual beats."
            ),
        ]
        if related_events:
            lines.append("Important events to preserve: " + " | ".join(related_events))
        return "\n".join(lines)

    def _first_important_event(
        self, parsed_results: list[ParsedChapterResult]
    ) -> ImportantEvent | None:
        for parsed_result in parsed_results:
            if parsed_result.important_events:
                return parsed_result.important_events[0]
        return None

    def _last_important_event(
        self, parsed_results: list[ParsedChapterResult]
    ) -> ImportantEvent | None:
        for parsed_result in reversed(parsed_results):
            if parsed_result.important_events:
                return parsed_result.important_events[-1]
        return None

    def _find_source_chapters(
        self, project: Project, selected_source_chapter_ids: list[str]
    ) -> list[SourceChapter]:
        chapters_by_id = {
            source_chapter.chapter_id: source_chapter
            for source_chapter in project.source_chapters
        }
        missing_ids = [
            chapter_id
            for chapter_id in selected_source_chapter_ids
            if chapter_id not in chapters_by_id
        ]
        if missing_ids:
            raise LookupError(
                "SourceChapter not found: " + ", ".join(missing_ids)
            )
        return [
            chapters_by_id[chapter_id]
            for chapter_id in selected_source_chapter_ids
        ]

    def _validate_plan_request(
        self,
        *,
        selected_source_chapter_ids: list[str],
        narration_style: str,
        retelling_density: str,
    ) -> None:
        if not selected_source_chapter_ids:
            raise ValueError("At least one source chapter must be selected.")
        if narration_style not in self._allowed_narration_styles:
            raise ValueError(f"Unsupported narration_style: {narration_style}")
        if retelling_density not in self._allowed_retelling_densities:
            raise ValueError(f"Unsupported retelling_density: {retelling_density}")
