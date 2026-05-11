"""Quality / readiness / repair / validation subcommands:

``score-prompts``, ``readiness-report``, ``batch-readiness-report``,
``suggest-repairs``, ``apply-repairs``, ``validate-project``.
"""

from __future__ import annotations

import argparse
import json

from app.cli._shared import (
    format_batch_readiness_report,
    format_prompt_quality_report,
    format_readiness_report,
    format_repair_actions_markdown,
    format_repair_actions_text,
    format_repair_results_text,
    format_validation_issues,
    load_project,
    parse_comma_separated,
)
from app.controllers.production_readiness_controller import (
    ProductionReadinessController,
)
from app.controllers.prompt_quality_controller import PromptQualityController
from app.controllers.repair_controller import RepairController
from app.controllers.validation_controller import ValidationController
from app.services.export_service import ExportService
from app.services.project_service import ProjectService


def register(subparsers: argparse._SubParsersAction) -> None:
    score_prompts = subparsers.add_parser("score-prompts")
    score_prompts.add_argument("--project", required=True)
    score_prompts.add_argument("--episode-id", required=True)
    score_prompts.add_argument("--format", default="text", choices=["text", "json", "markdown"])
    score_prompts.add_argument("--output", default=None)
    score_prompts.set_defaults(handler=handle_score_prompts)

    readiness_report = subparsers.add_parser("readiness-report")
    readiness_report.add_argument("--project", required=True)
    readiness_report.add_argument("--episode-id", required=True)
    readiness_report.add_argument(
        "--format",
        default="text",
        choices=["text", "json", "markdown"],
    )
    readiness_report.add_argument("--output", default=None)
    readiness_report.add_argument("--fail-if-blocked", action="store_true")
    readiness_report.set_defaults(handler=handle_readiness_report)

    batch_readiness = subparsers.add_parser("batch-readiness-report")
    batch_readiness.add_argument("--project", required=True)
    batch_readiness.add_argument("--episode-ids", required=True)
    batch_readiness.add_argument(
        "--format",
        default="markdown",
        choices=["text", "json", "markdown"],
    )
    batch_readiness.add_argument("--output", default=None)
    batch_readiness.add_argument("--fail-if-blocked", action="store_true")
    batch_readiness.set_defaults(handler=handle_batch_readiness_report)

    suggest_repairs = subparsers.add_parser("suggest-repairs")
    suggest_repairs.add_argument("--project", required=True)
    suggest_repairs.add_argument("--episode-id", required=True)
    suggest_repairs.add_argument(
        "--format",
        default="text",
        choices=["text", "json", "markdown"],
    )
    suggest_repairs.add_argument("--output", default=None)
    suggest_repairs.set_defaults(handler=handle_suggest_repairs)

    apply_repairs = subparsers.add_parser("apply-repairs")
    apply_repairs.add_argument("--project", required=True)
    apply_repairs.add_argument("--episode-id", required=True)
    apply_repairs.add_argument("--action-id", default=None)
    apply_repairs.add_argument("--low-risk-only", action="store_true")
    apply_repairs.add_argument("--allow-medium-risk", action="store_true")
    apply_repairs.add_argument("--allow-high-risk", action="store_true")
    apply_repairs.add_argument("--save", action="store_true")
    apply_repairs.set_defaults(handler=handle_apply_repairs)

    validate_project = subparsers.add_parser("validate-project")
    validate_project.add_argument("--project", required=True)
    validate_project.add_argument("--episode-id", default=None)
    validate_project.add_argument("--format", default="text", choices=["text", "json"])
    validate_project.add_argument("--fail-on-error", action="store_true")
    validate_project.set_defaults(handler=handle_validate_project)


def handle_score_prompts(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    controller = PromptQualityController(project_service)
    if args.format == "json":
        content = (
            json.dumps(
                controller.build_episode_report(project, args.episode_id),
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
    elif args.format == "markdown":
        content = controller.export_episode_report_markdown(project, args.episode_id)
    else:
        content = format_prompt_quality_report(
            controller.build_episode_report(project, args.episode_id)
        )

    if args.output:
        ExportService(project_service).write_text_file(content, args.output)
        print(f"Wrote prompt quality report: {args.output}")
    else:
        print(content.rstrip())
    return 0


def handle_readiness_report(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    controller = ProductionReadinessController(project_service)
    report = controller.build_episode_report(project, args.episode_id)

    if args.format == "json":
        content = json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n"
    elif args.format == "markdown":
        content = controller.export_episode_report_markdown(
            project,
            args.episode_id,
        )
    else:
        content = format_readiness_report(report.to_dict())

    if args.output:
        ExportService(project_service).write_text_file(content, args.output)
        print(f"Wrote production readiness report: {args.output}")
    else:
        print(content.rstrip())

    if args.fail_if_blocked and report.status == "blocked":
        return 1
    return 0


def handle_batch_readiness_report(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    controller = ProductionReadinessController(project_service)
    episode_ids = parse_comma_separated(args.episode_ids)
    batch = controller.build_batch_report(project, episode_ids)

    if args.format == "json":
        content = json.dumps(batch, ensure_ascii=False, indent=2) + "\n"
    elif args.format == "markdown":
        content = controller.export_batch_report_markdown(project, episode_ids)
    else:
        content = format_batch_readiness_report(batch)

    if args.output:
        ExportService(project_service).write_text_file(content, args.output)
        print(f"Wrote batch readiness report: {args.output}")
    else:
        print(content.rstrip())

    if args.fail_if_blocked and batch.get("blocked_count", 0):
        return 1
    return 0


def handle_suggest_repairs(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    controller = RepairController(project_service)
    actions = controller.suggest_repairs_for_episode(project, args.episode_id)

    if args.format == "json":
        content = (
            json.dumps(
                [action.to_dict() for action in actions],
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
    elif args.format == "markdown":
        content = format_repair_actions_markdown(actions)
    else:
        content = format_repair_actions_text(actions)

    if args.output:
        ExportService(project_service).write_text_file(content, args.output)
        print(f"Wrote repair suggestions: {args.output}")
    else:
        print(content.rstrip())
    return 0


def handle_apply_repairs(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    controller = RepairController(project_service)
    actions = controller.suggest_repairs_for_episode(project, args.episode_id)

    if args.action_id:
        results = [
            controller.apply_repair_action(
                project,
                args.action_id,
                actions,
                allow_medium_risk=args.allow_medium_risk,
                allow_high_risk=args.allow_high_risk,
            )
        ]
    elif args.low_risk_only:
        results = controller.apply_low_risk_repairs(project, actions)
    else:
        raise ValueError("apply-repairs requires --action-id or --low-risk-only.")

    if args.save and any(result.applied for result in results):
        project_service.save_project(project, args.project)

    print(format_repair_results_text(results))
    return 0


def handle_validate_project(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    controller = ValidationController(project_service)
    issues = controller.validate_project(project, episode_id=args.episode_id)

    if args.format == "json":
        print(
            json.dumps(
                [issue.to_dict() for issue in issues],
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(format_validation_issues(issues))

    if args.fail_on_error and controller.has_errors(issues):
        return 1
    return 0
