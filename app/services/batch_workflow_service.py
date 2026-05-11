"""Batch orchestration for multi-chapter review episode workflows."""

from __future__ import annotations

import re
from pathlib import Path

from app.domain.episode import ReviewEpisode
from app.domain.project import Project
from app.domain.source_chapter import SourceChapter
from app.domain.validation import ValidationIssue
from app.infrastructure.ai_gateway import AIGateway
from app.services.beat_generator_service import BeatGeneratorService
from app.services.continuity_checker_service import ContinuityCheckerService
from app.services.episode_planner_service import EpisodePlannerService
from app.services.export_service import ExportService
from app.services.project_service import ProjectService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.quality.validation import ProjectValidationService
from app.services.review_rewriter_service import ReviewRewriterService


class BatchWorkflowService:
    EXPORT_FILE_PARTS = {
        "markdown": (".md", ""),
        "json": (".json", ""),
        "csv": (".csv", ""),
        "review-txt": (".txt", "_review"),
        "prompts-txt": (".txt", "_prompts"),
    }

    def __init__(
        self,
        project_service: ProjectService | None = None,
        ai_gateway: AIGateway | None = None,
        export_service: ExportService | None = None,
        project_validation_service: ProjectValidationService | None = None,
        continuity_checker_service: ContinuityCheckerService | None = None,
    ) -> None:
        self.project_service = project_service or ProjectService()
        self.ai_gateway = ai_gateway
        self.export_service = export_service or ExportService(self.project_service)
        self.project_validation_service = project_validation_service or ProjectValidationService()
        self.continuity_checker_service = continuity_checker_service or ContinuityCheckerService(
            self.project_service
        )
        self.last_validation_issues: dict[str, list[ValidationIssue]] = {}

    def plan_episodes_from_chapters(
        self,
        project: Project,
        chapter_ids: list[str],
        chapters_per_episode: int = 1,
        tone: str | None = None,
        density: str | None = None,
        use_ai: bool = False,
    ) -> list[ReviewEpisode]:
        selected_chapter_ids = self._clean_ids(chapter_ids)
        if not selected_chapter_ids:
            raise ValueError("At least one source chapter id is required.")
        if chapters_per_episode < 1:
            raise ValueError("chapters_per_episode must be at least 1.")

        chapters_by_id = self._chapters_by_id(project)
        missing_ids = [
            chapter_id for chapter_id in selected_chapter_ids if chapter_id not in chapters_by_id
        ]
        if missing_ids:
            raise LookupError("SourceChapter not found: " + ", ".join(missing_ids))

        narration_style = tone or project.default_narration_style
        retelling_density = density or project.retelling_density
        planned_episodes: list[ReviewEpisode] = []

        for group_index, group in enumerate(
            self._chapter_groups(selected_chapter_ids, chapters_per_episode),
            start=1,
        ):
            existing_episode = self._find_existing_episode(
                project,
                group,
                narration_style,
                retelling_density,
            )
            if existing_episode is not None:
                planned_episodes.append(existing_episode)
                continue

            source_chapters = [chapters_by_id[chapter_id] for chapter_id in group]
            episode_title = self._episode_title_for_group(
                group_index,
                source_chapters,
            )
            episode = EpisodePlannerService(
                self.project_service,
                ai_gateway=self.ai_gateway,
                use_ai=use_ai,
            ).plan_episode(
                project,
                selected_source_chapter_ids=list(group),
                narration_style=narration_style,
                retelling_density=retelling_density,
                episode_title=episode_title,
            )
            planned_episodes.append(episode)

        return planned_episodes

    def run_generation_for_episodes(
        self,
        project: Project,
        episode_ids: list[str],
        tone: str | None = None,
        density: str | None = None,
        style_preset_id: str | None = None,
        use_ai: bool = False,
        validate: bool = False,
        fail_on_validation_error: bool = False,
    ) -> list[ReviewEpisode]:
        selected_episode_ids = self._clean_ids(episode_ids)
        if not selected_episode_ids:
            raise ValueError("At least one review episode id is required.")

        generated_episodes: list[ReviewEpisode] = []
        self.last_validation_issues = {}

        for episode_id in selected_episode_ids:
            episode = self.project_service.find_episode(project, episode_id)
            if tone is not None:
                episode.tone = tone
            if density is not None:
                episode.density = density

            BeatGeneratorService(
                self.project_service,
                ai_gateway=self.ai_gateway,
                use_ai=use_ai,
            ).generate_beats_for_episode(
                project,
                episode_id,
                retelling_density=density,
            )
            ReviewRewriterService(
                ai_gateway=self.ai_gateway,
                use_ai=use_ai,
            ).rewrite_episode(
                project,
                episode_id,
                narration_style=tone,
                retelling_density=density,
            )
            PromptBuilderService(
                ai_gateway=self.ai_gateway,
                use_ai=use_ai,
            ).build_prompts_for_episode(
                project,
                episode_id,
                style_preset_id=style_preset_id,
            )

            if validate:
                issues = self._validate_episode(project, episode_id)
                self.last_validation_issues[episode_id] = issues
                if fail_on_validation_error and self._has_errors(issues):
                    raise ValueError(
                        "Batch validation failed for "
                        f"{episode_id}: {self._issue_summary(issues)}"
                    )

            generated_episodes.append(episode)

        project.touch()
        return generated_episodes

    def export_episodes(
        self,
        project: Project,
        episode_ids: list[str],
        output_dir: str | Path,
        formats: list[str],
    ) -> list[Path]:
        selected_episode_ids = self._clean_ids(episode_ids)
        export_formats = self._clean_ids(formats)
        if not selected_episode_ids:
            raise ValueError("At least one review episode id is required.")
        if not export_formats:
            raise ValueError("At least one export format is required.")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        written_paths: list[Path] = []

        for episode_id in selected_episode_ids:
            episode = self.project_service.find_episode(project, episode_id)
            for export_format in export_formats:
                path = output_path / self._export_filename(episode, export_format)
                written_paths.append(
                    self._write_export(project, episode.episode_id, export_format, path)
                )

        return written_paths

    def _write_export(
        self,
        project: Project,
        episode_id: str,
        export_format: str,
        output_path: Path,
    ) -> Path:
        if export_format == "markdown":
            return self.export_service.write_text_file(
                self.export_service.export_episode_markdown(project, episode_id),
                output_path,
            )
        if export_format == "json":
            return self.export_service.write_json_file(
                self.export_service.export_episode_json(project, episode_id),
                output_path,
            )
        if export_format == "csv":
            return self.export_service.write_text_file(
                self.export_service.export_episode_csv(project, episode_id),
                output_path,
            )
        if export_format == "review-txt":
            return self.export_service.write_text_file(
                self.export_service.export_review_script_txt(project, episode_id),
                output_path,
            )
        if export_format == "prompts-txt":
            return self.export_service.write_text_file(
                self.export_service.export_image_prompts_txt(project, episode_id),
                output_path,
            )
        raise ValueError(f"Unsupported export format: {export_format}")

    def _find_existing_episode(
        self,
        project: Project,
        chapter_ids: list[str],
        tone: str,
        density: str,
    ) -> ReviewEpisode | None:
        for episode in project.review_episodes:
            if (
                episode.source_chapter_ids == list(chapter_ids)
                and episode.tone == tone
                and episode.density == density
            ):
                return episode
        return None

    def _chapter_groups(
        self,
        chapter_ids: list[str],
        chapters_per_episode: int,
    ) -> list[list[str]]:
        return [
            chapter_ids[index : index + chapters_per_episode]
            for index in range(0, len(chapter_ids), chapters_per_episode)
        ]

    def _episode_title_for_group(
        self,
        group_index: int,
        source_chapters: list[SourceChapter],
    ) -> str:
        first = source_chapters[0]
        last = source_chapters[-1]
        if first.chapter_id == last.chapter_id:
            coverage = first.title
        else:
            coverage = f"{first.title} - {last.title}"
        return f"Episode {group_index}: {coverage}"

    def _validate_episode(
        self,
        project: Project,
        episode_id: str,
    ) -> list[ValidationIssue]:
        issues = self.project_validation_service.validate_episode(
            project,
            episode_id,
        )
        try:
            issues.extend(self.continuity_checker_service.check_episode(project, episode_id))
        except LookupError as exc:
            issues.append(
                ValidationIssue(
                    issue_id=f"val_{len(issues) + 1:03d}",
                    severity="error",
                    category="broken_reference",
                    message=str(exc),
                    suggestion="Choose an existing review episode.",
                    entity_type="ReviewEpisode",
                    entity_id=episode_id,
                    episode_id=episode_id,
                )
            )
        return issues

    def _has_errors(self, issues: list[ValidationIssue]) -> bool:
        return any(issue.severity == "error" for issue in issues)

    def _export_filename(
        self,
        episode: ReviewEpisode,
        export_format: str,
    ) -> str:
        if export_format not in self.EXPORT_FILE_PARTS:
            raise ValueError(f"Unsupported export format: {export_format}")
        extension, marker = self.EXPORT_FILE_PARTS[export_format]
        return f"{self._episode_file_stem(episode.episode_id)}{marker}{extension}"

    def _episode_file_stem(self, episode_id: str) -> str:
        match = re.search(r"(\d+)$", episode_id)
        if match:
            return f"episode_{match.group(1).zfill(3)}"
        safe_id = re.sub(r"[^a-zA-Z0-9]+", "_", episode_id).strip("_")
        return f"episode_{safe_id or 'review'}"

    def _chapters_by_id(self, project: Project) -> dict[str, SourceChapter]:
        return {chapter.chapter_id: chapter for chapter in project.source_chapters}

    def _clean_ids(self, values: list[str]) -> list[str]:
        return [value.strip() for value in values if value and value.strip()]

    def _issue_summary(self, issues: list[ValidationIssue]) -> str:
        errors = [issue for issue in issues if issue.severity == "error"]
        if not errors:
            return "no error severity issues"
        return "; ".join(
            f"{issue.category} on {issue.entity_id or issue.entity_type}" for issue in errors[:3]
        )
