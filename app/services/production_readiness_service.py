"""Production readiness reports for episodes and batches."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from typing import Any, Callable

from app.domain.episode import ReviewEpisode
from app.domain.production_readiness import ProductionReadinessReport
from app.domain.project import Project
from app.domain.validation import ValidationIssue
from app.services.continuity_checker_service import ContinuityCheckerService
from app.services.export_service import ExportService
from app.services.project_service import ProjectService
from app.services.project_validation_service import ProjectValidationService
from app.services.prompt_quality_service import PromptQualityService
from app.services.review_quality_service import ReviewQualityService


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProductionReadinessService:
    def __init__(
        self,
        project_service: ProjectService | None = None,
        validation_service: ProjectValidationService | None = None,
        continuity_checker: ContinuityCheckerService | None = None,
        review_quality_service: ReviewQualityService | None = None,
        prompt_quality_service: PromptQualityService | None = None,
        export_service: ExportService | None = None,
        generated_at_factory: Callable[[], str] | None = None,
    ) -> None:
        self.project_service = project_service or ProjectService()
        self.validation_service = validation_service or ProjectValidationService()
        self.continuity_checker = continuity_checker or ContinuityCheckerService(
            self.project_service
        )
        self.review_quality_service = review_quality_service or ReviewQualityService(
            self.project_service
        )
        self.prompt_quality_service = prompt_quality_service or PromptQualityService(
            self.project_service
        )
        self.export_service = export_service or ExportService(self.project_service)
        self.generated_at_factory = generated_at_factory or _utc_now_iso

    def build_episode_report(
        self,
        project: Project,
        episode_id: str,
    ) -> ProductionReadinessReport:
        episode = self.project_service.find_episode(project, episode_id)
        validation_issues = self.validation_service.validate_episode(project, episode_id)
        continuity_issues = self.continuity_checker.check_episode(project, episode_id)
        review_summary = self.review_quality_service.build_episode_report(
            project,
            episode_id,
        )
        prompt_summary = self.prompt_quality_service.build_episode_report(
            project,
            episode_id,
        )
        export_readiness = self._build_export_readiness(
            project,
            episode,
            validation_issues,
        )

        total_beats = self._total_beats(episode)
        review_average = float(review_summary.get("average_score", 0.0))
        prompt_average = float(prompt_summary.get("average_score", 0.0))
        validation_error_count = self._count_severity(validation_issues, "error")
        validation_warning_count = self._count_severity(validation_issues, "warning")
        issue_health = self._issue_health_score(validation_issues, continuity_issues)
        overall_score = round(
            review_average * 0.4 + prompt_average * 0.4 + issue_health * 0.2
        )
        blocked_reasons = self._blocked_reasons(
            validation_issues,
            export_readiness,
            review_average,
            prompt_average,
            total_beats,
        )
        top_recommendations = self._top_recommendations(
            validation_issues,
            continuity_issues,
            review_summary,
            prompt_summary,
            export_readiness,
        )
        status = self._status(
            blocked_reasons,
            validation_issues,
            continuity_issues,
            export_readiness,
            review_average,
            prompt_average,
        )

        return ProductionReadinessReport(
            project_id=project.project_id,
            project_title=project.title,
            episode_id=episode.episode_id,
            episode_title=episode.title,
            status=status,
            overall_score=overall_score,
            validation_error_count=validation_error_count,
            validation_warning_count=validation_warning_count,
            continuity_issue_count=len(continuity_issues),
            review_average_score=review_average,
            prompt_average_score=prompt_average,
            total_beats=total_beats,
            ready_review_beats=int(review_summary.get("ready_count", 0)),
            ready_prompt_beats=int(prompt_summary.get("ready_count", 0)),
            blocked_reasons=blocked_reasons,
            top_recommendations=top_recommendations,
            validation_issues=validation_issues,
            continuity_issues=continuity_issues,
            review_quality_summary=review_summary,
            prompt_quality_summary=prompt_summary,
            export_readiness=export_readiness,
            generated_at=self.generated_at_factory(),
        )

    def build_batch_report(
        self,
        project: Project,
        episode_ids: list[str],
    ) -> dict[str, Any]:
        reports = [
            self.build_episode_report(project, episode_id) for episode_id in episode_ids
        ]
        status_counts = Counter(report.status for report in reports)
        average_score = (
            round(sum(report.overall_score for report in reports) / len(reports), 2)
            if reports
            else 0.0
        )
        return {
            "project_id": project.project_id,
            "project_title": project.title,
            "episode_count": len(reports),
            "average_score": average_score,
            "status_counts": dict(status_counts),
            "ready_count": status_counts.get("ready", 0),
            "needs_review_count": status_counts.get("needs_review", 0),
            "blocked_count": status_counts.get("blocked", 0),
            "reports": [report.to_dict() for report in reports],
            "generated_at": self.generated_at_factory(),
        }

    def export_episode_report_markdown(
        self,
        project: Project,
        episode_id: str,
    ) -> str:
        report = self.build_episode_report(project, episode_id)
        return self._episode_markdown(report)

    def export_batch_report_markdown(
        self,
        project: Project,
        episode_ids: list[str],
    ) -> str:
        batch = self.build_batch_report(project, episode_ids)
        lines = [
            "# Batch Production Readiness Report",
            "",
            f"- Project title: {batch['project_title']}",
            f"- Episodes: {batch['episode_count']}",
            f"- Average score: {batch['average_score']}",
            f"- Ready: {batch['ready_count']}",
            f"- Needs review: {batch['needs_review_count']}",
            f"- Blocked: {batch['blocked_count']}",
            "",
            "## Episodes",
            "",
            "| Episode | Status | Overall Score | Review Avg | Prompt Avg |",
            "|---|---|---:|---:|---:|",
        ]
        for item in batch["reports"]:
            lines.append(
                f"| {item['episode_title']} | {item['status']} | "
                f"{item['overall_score']} | {item['review_average_score']} | "
                f"{item['prompt_average_score']} |"
            )
        return "\n".join(lines).rstrip() + "\n"

    def export_episode_report_json(
        self,
        project: Project,
        episode_id: str,
    ) -> dict[str, Any]:
        return self.build_episode_report(project, episode_id).to_dict()

    def _build_export_readiness(
        self,
        project: Project,
        episode: ReviewEpisode,
        validation_issues: list[ValidationIssue],
    ) -> dict[str, Any]:
        scenes = list(episode.scenes)
        beats = [
            beat
            for scene in scenes
            for beat in scene.ordered_beats()
        ]
        checks: dict[str, Any] = {
            "episode_exists": True,
            "has_scenes": bool(scenes),
            "has_beats": bool(beats),
            "all_beats_have_review_text": all(
                bool(beat.review_text.strip()) for beat in beats
            )
            if beats
            else False,
            "all_beats_have_image_prompt": all(
                bool(beat.image_prompt.strip()) for beat in beats
            )
            if beats
            else False,
            "all_beats_have_negative_prompt": all(
                bool(beat.negative_prompt.strip()) for beat in beats
            )
            if beats
            else False,
            "no_validation_errors": not self.validation_service.has_errors(
                validation_issues
            ),
            "markdown_exportable": False,
            "json_exportable": False,
            "csv_exportable": False,
            "errors": [],
        }

        self._try_export(checks, "markdown_exportable", lambda: self.export_service.export_episode_markdown(project, episode.episode_id))
        self._try_export(
            checks,
            "json_exportable",
            lambda: json.dumps(
                self.export_service.export_episode_json(project, episode.episode_id),
                ensure_ascii=False,
            ),
        )
        self._try_export(checks, "csv_exportable", lambda: self.export_service.export_episode_csv(project, episode.episode_id))
        checks["is_ready"] = all(
            checks[key]
            for key in [
                "has_scenes",
                "has_beats",
                "all_beats_have_review_text",
                "all_beats_have_image_prompt",
                "all_beats_have_negative_prompt",
                "no_validation_errors",
                "markdown_exportable",
                "json_exportable",
                "csv_exportable",
            ]
        )
        return checks

    def _try_export(
        self,
        checks: dict[str, Any],
        key: str,
        export_fn: Callable[[], Any],
    ) -> None:
        try:
            export_fn()
        except Exception as exc:
            checks["errors"].append(f"{key}: {exc}")
        else:
            checks[key] = True

    def _blocked_reasons(
        self,
        validation_issues: list[ValidationIssue],
        export_readiness: dict[str, Any],
        review_average: float,
        prompt_average: float,
        total_beats: int,
    ) -> list[str]:
        reasons: list[str] = []
        if self.validation_service.has_errors(validation_issues):
            reasons.append("Validation errors must be fixed before export.")
        if not export_readiness.get("has_scenes"):
            reasons.append("Episode has no scenes.")
        if not export_readiness.get("has_beats") or total_beats == 0:
            reasons.append("Episode has no beats.")
        if not export_readiness.get("all_beats_have_review_text"):
            reasons.append("Some beats are missing review text.")
        if not export_readiness.get("all_beats_have_image_prompt"):
            reasons.append("Some beats are missing image prompts.")
        if not export_readiness.get("all_beats_have_negative_prompt"):
            reasons.append("Some beats are missing negative prompts.")
        if review_average < 60:
            reasons.append("Average review narration quality is below 60.")
        if prompt_average < 60:
            reasons.append("Average prompt quality is below 60.")
        for error in export_readiness.get("errors", []):
            reasons.append(f"Export check failed: {error}")
        return list(dict.fromkeys(reasons))

    def _status(
        self,
        blocked_reasons: list[str],
        validation_issues: list[ValidationIssue],
        continuity_issues: list[ValidationIssue],
        export_readiness: dict[str, Any],
        review_average: float,
        prompt_average: float,
    ) -> str:
        if blocked_reasons:
            return "blocked"
        if any(issue.severity == "error" for issue in continuity_issues):
            return "blocked"
        if not export_readiness.get("is_ready"):
            return "blocked"
        if review_average >= 80 and prompt_average >= 80:
            has_warning = any(
                issue.severity == "warning"
                for issue in [*validation_issues, *continuity_issues]
            )
            return "needs_review" if has_warning else "ready"
        if review_average >= 60 and prompt_average >= 60:
            return "needs_review"
        return "blocked"

    def _top_recommendations(
        self,
        validation_issues: list[ValidationIssue],
        continuity_issues: list[ValidationIssue],
        review_summary: dict[str, Any],
        prompt_summary: dict[str, Any],
        export_readiness: dict[str, Any],
    ) -> list[str]:
        categories = {
            issue.category for issue in [*validation_issues, *continuity_issues]
        }
        recommendations: list[str] = []

        if not export_readiness.get("all_beats_have_review_text") or "empty_review_text" in categories:
            recommendations.append("Run rewrite-review for missing beats.")
        if not export_readiness.get("all_beats_have_image_prompt") or "empty_image_prompt" in categories:
            recommendations.append("Run build-prompts for missing beats.")
        if not export_readiness.get("all_beats_have_negative_prompt") or "empty_negative_prompt" in categories:
            recommendations.append("Add negative prompts for beats that already have image prompts.")
        if "broken_reference" in categories:
            recommendations.append("Fix broken episode, scene, beat, or bible references before export.")
        if "character_missing_visual_base" in categories:
            recommendations.append("Update Character Bible visual_prompt_base.")
        if "location_missing_visual_base" in categories:
            recommendations.append("Update Location Bible visual_prompt_base.")
        if categories.intersection(
            {
                "outfit_continuity",
                "prompt_missing_character_detail",
                "prompt_missing_location_detail",
                "location_continuity",
            }
        ):
            recommendations.append("Review bible and prompt consistency for flagged beats.")
        if float(prompt_summary.get("average_score", 0.0)) < 80:
            recommendations.append("Review prompts flagged by PromptQualityService.")
        if float(review_summary.get("average_score", 0.0)) < 80:
            recommendations.append("Improve review narration for low-scoring beats.")
        if not export_readiness.get("is_ready"):
            recommendations.append("Complete missing review text, prompts, and negative prompts before export.")

        return list(dict.fromkeys(recommendations))[:8]

    def _issue_health_score(
        self,
        validation_issues: list[ValidationIssue],
        continuity_issues: list[ValidationIssue],
    ) -> int:
        score = 100
        for issue in [*validation_issues, *continuity_issues]:
            if issue.severity == "error":
                score -= 20
            elif issue.severity == "warning":
                score -= 5
            elif issue.severity == "info":
                score -= 1
        return max(0, score)

    def _episode_markdown(self, report: ProductionReadinessReport) -> str:
        data = report.to_dict()
        lines = [
            "# Production Readiness Report",
            "",
            f"- Project title: {data['project_title']}",
            f"- Episode title: {data['episode_title']}",
            f"- Status: {data['status']}",
            f"- Overall score: {data['overall_score']}",
            f"- Review average score: {data['review_average_score']}",
            f"- Prompt average score: {data['prompt_average_score']}",
            f"- Validation errors: {data['validation_error_count']}",
            f"- Validation warnings: {data['validation_warning_count']}",
            f"- Continuity issues: {data['continuity_issue_count']}",
            f"- Export ready: {str(data['export_readiness'].get('is_ready', False)).lower()}",
            "",
            "## Blocked Reasons",
            "",
        ]
        lines.extend(self._bullets(data["blocked_reasons"]))
        lines.extend(["", "## Top Recommendations", ""])
        lines.extend(self._bullets(data["top_recommendations"]))
        lines.extend(["", "## Worst Review Beats", ""])
        lines.extend(
            self._worst_beats(
                data["review_quality_summary"].get("worst_beats", []),
            )
        )
        lines.extend(["", "## Worst Prompt Beats", ""])
        lines.extend(
            self._worst_beats(
                data["prompt_quality_summary"].get("worst_beats", []),
            )
        )
        lines.extend(["", "## Validation And Continuity Issues", ""])
        issues = [
            *data["validation_issues"],
            *data["continuity_issues"],
        ]
        if issues:
            for issue in issues:
                target = issue.get("beat_id") or issue.get("scene_id") or issue.get("entity_id") or issue.get("entity_type") or "project"
                lines.append(
                    f"- [{issue['severity']}] {issue['category']} ({target}): {issue['message']}"
                )
        else:
            lines.append("- None")
        return "\n".join(lines).rstrip() + "\n"

    def _bullets(self, values: list[str]) -> list[str]:
        if not values:
            return ["- None"]
        return [f"- {value}" for value in values]

    def _worst_beats(self, values: list[dict[str, Any]]) -> list[str]:
        if not values:
            return ["- None"]
        return [
            f"- `{item['beat_id']}`: {item['score']} ({item['grade']})"
            for item in values[:5]
        ]

    def _count_severity(
        self,
        issues: list[ValidationIssue],
        severity: str,
    ) -> int:
        return sum(1 for issue in issues if issue.severity == severity)

    def _total_beats(self, episode: ReviewEpisode) -> int:
        return sum(len(scene.beats) for scene in episode.scenes)
