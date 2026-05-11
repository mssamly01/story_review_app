"""Helpers shared across the ``story-review`` subcommand modules."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from app.domain.project import Project
from app.infrastructure.ai_gateway import AIGateway
from app.infrastructure.ai_gateway_factory import create_ai_gateway
from app.services.export_service import ExportService
from app.services.project_service import ProjectService


def add_ai_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--use-ai", action="store_true")
    parser.add_argument("--mock-ai", action="store_true")
    parser.add_argument("--real-ai", action="store_true")
    parser.add_argument("--model", default=None)


def parse_comma_separated(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def load_project(project_service: ProjectService, path: str | Path) -> Project:
    project_path = Path(path)
    if not project_path.exists():
        raise FileNotFoundError(f"Project file not found: {project_path}")
    return project_service.load_project(project_path)


def find_chapter(project: Project, chapter_id: str):
    for chapter in project.source_chapters:
        if chapter.chapter_id == chapter_id:
            return chapter
    raise LookupError(f"SourceChapter not found: {chapter_id}")


def should_use_ai(args: argparse.Namespace) -> bool:
    return bool(
        getattr(args, "use_ai", False)
        or getattr(args, "mock_ai", False)
        or getattr(args, "real_ai", False)
    )


def build_gateway(args: argparse.Namespace) -> AIGateway | None:
    return create_ai_gateway(
        use_ai=should_use_ai(args),
        mock_ai=bool(getattr(args, "mock_ai", False)),
        real_ai=bool(getattr(args, "real_ai", False)),
        model=getattr(args, "model", None),
    )


def write_export(
    project_service: ProjectService,
    project: Project,
    episode_id: str,
    export_format: str,
    output_path: str | Path,
) -> Path:
    export_service = ExportService(project_service)
    if export_format == "markdown":
        return export_service.write_text_file(
            export_service.export_episode_markdown(project, episode_id),
            output_path,
        )
    if export_format == "json":
        return export_service.write_json_file(
            export_service.export_episode_json(project, episode_id),
            output_path,
        )
    if export_format == "csv":
        return export_service.write_text_file(
            export_service.export_episode_csv(project, episode_id),
            output_path,
        )
    if export_format == "review-txt":
        return export_service.write_text_file(
            export_service.export_review_script_txt(project, episode_id),
            output_path,
        )
    if export_format == "prompts-txt":
        return export_service.write_text_file(
            export_service.export_image_prompts_txt(project, episode_id),
            output_path,
        )
    raise ValueError(f"Unsupported export format: {export_format}")


def format_validation_issues(issues: list[Any]) -> str:
    if not issues:
        return "No validation issues found."

    error_count = sum(1 for issue in issues if issue.severity == "error")
    warning_count = sum(1 for issue in issues if issue.severity == "warning")
    info_count = sum(1 for issue in issues if issue.severity == "info")
    lines = [
        (
            "Validation issues: "
            f"{len(issues)} "
            f"(errors: {error_count}, warnings: {warning_count}, info: {info_count})"
        )
    ]
    for issue in issues:
        target = issue.entity_type or "Project"
        if issue.entity_id:
            target = f"{target} {issue.entity_id}"
        lines.append(f"[{issue.severity}] {issue.category} - {target}: {issue.message}")
        if issue.suggestion:
            lines.append(f"  Suggestion: {issue.suggestion}")
    return "\n".join(lines)


def format_prompt_quality_report(report: dict[str, Any]) -> str:
    lines = [
        f"Prompt quality report: {report['episode_title']}",
        f"Average score: {report['average_score']}",
        f"Ready: {report['ready_count']}",
        f"Not ready: {report['not_ready_count']}",
        "Grade distribution: "
        + ", ".join(
            f"{grade}={report['grade_distribution'].get(grade, 0)}"
            for grade in ["A", "B", "C", "D", "F"]
        ),
    ]
    if report["common_issues"]:
        lines.append(
            "Common issues: "
            + ", ".join(
                f"{item['category']} ({item['count']})" for item in report["common_issues"][:5]
            )
        )
    else:
        lines.append("Common issues: none")
    return "\n".join(lines)


def format_readiness_report(report: dict[str, Any]) -> str:
    lines = [
        f"Production readiness report: {report['episode_title']}",
        f"Status: {report['status']}",
        f"Overall score: {report['overall_score']}",
        f"Review average score: {report['review_average_score']}",
        f"Prompt average score: {report['prompt_average_score']}",
        (
            "Issues: "
            f"errors={report['validation_error_count']}, "
            f"warnings={report['validation_warning_count']}, "
            f"continuity={report['continuity_issue_count']}"
        ),
        f"Export ready: {report['export_readiness'].get('is_ready', False)}",
    ]
    if report["blocked_reasons"]:
        lines.append("Blocked reasons: " + "; ".join(report["blocked_reasons"][:5]))
    if report["top_recommendations"]:
        lines.append("Recommendations: " + "; ".join(report["top_recommendations"][:5]))
    return "\n".join(lines)


def format_batch_readiness_report(report: dict[str, Any]) -> str:
    lines = [
        f"Batch production readiness report: {report['project_title']}",
        f"Episodes: {report['episode_count']}",
        f"Average score: {report['average_score']}",
        (
            "Status counts: "
            f"ready={report['ready_count']}, "
            f"needs_review={report['needs_review_count']}, "
            f"blocked={report['blocked_count']}"
        ),
    ]
    for item in report["reports"]:
        lines.append(f"- {item['episode_id']}: {item['status']} " f"({item['overall_score']})")
    return "\n".join(lines)


def format_repair_actions_text(actions: list[Any]) -> str:
    if not actions:
        return "No repair suggestions found."
    lines = [f"Repair suggestions: {len(actions)}"]
    for action in actions:
        lines.append(
            f"- {action.action_id}: {action.action_type} " f"[{action.risk_level}] {action.title}"
        )
        lines.append(f"  Target: {action.target_entity_type} {action.target_entity_id}")
        lines.append(f"  Auto apply: {action.can_auto_apply}")
    return "\n".join(lines)


def format_repair_actions_markdown(actions: list[Any]) -> str:
    lines = [
        "# Repair Suggestions",
        "",
        "| Action ID | Type | Risk | Target | Auto Apply | Title |",
        "|---|---|---|---|---|---|",
    ]
    for action in actions:
        target = f"{action.target_entity_type} {action.target_entity_id}".strip()
        lines.append(
            f"| `{action.action_id}` | {action.action_type} | {action.risk_level} | "
            f"{target} | {str(action.can_auto_apply).lower()} | {action.title} |"
        )
    if not actions:
        lines.append("| - | none | - | - | - | No repair suggestions found. |")
    return "\n".join(lines).rstrip() + "\n"


def format_repair_results_text(results: list[Any]) -> str:
    if not results:
        return "No repairs applied."
    lines = [f"Repair results: {len(results)}"]
    for result in results:
        status = "applied" if result.applied else "skipped"
        lines.append(f"- {result.action_id}: {status} - {result.message}")
    return "\n".join(lines)
