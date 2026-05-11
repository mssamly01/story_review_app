"""``plan-batch-episodes``, ``run-batch-pipeline`` — multi-episode automation."""

from __future__ import annotations

import argparse

from app.cli._shared import (
    add_ai_flags,
    build_gateway,
    load_project,
    parse_comma_separated,
    should_use_ai,
)
from app.services.batch_workflow_service import BatchWorkflowService
from app.services.project_service import ProjectService


def register(subparsers: argparse._SubParsersAction) -> None:
    plan_batch = subparsers.add_parser("plan-batch-episodes")
    plan_batch.add_argument("--project", required=True)
    plan_batch.add_argument("--chapter-ids", required=True)
    plan_batch.add_argument("--chapters-per-episode", default=1, type=int)
    plan_batch.add_argument("--tone", default=None)
    plan_batch.add_argument("--density", default=None)
    add_ai_flags(plan_batch)
    plan_batch.set_defaults(handler=handle_plan_batch_episodes)

    batch_pipeline = subparsers.add_parser("run-batch-pipeline")
    batch_pipeline.add_argument("--project", required=True)
    batch_pipeline.add_argument("--episode-ids", required=True)
    batch_pipeline.add_argument("--output-dir", required=True)
    batch_pipeline.add_argument("--tone", default=None)
    batch_pipeline.add_argument("--density", default=None)
    batch_pipeline.add_argument("--style-preset-id", default=None)
    batch_pipeline.add_argument("--export-formats", default="markdown")
    batch_pipeline.add_argument("--validate", action="store_true")
    batch_pipeline.add_argument("--fail-on-validation-error", action="store_true")
    add_ai_flags(batch_pipeline)
    batch_pipeline.set_defaults(handler=handle_run_batch_pipeline)


def handle_plan_batch_episodes(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    service = BatchWorkflowService(
        project_service,
        ai_gateway=build_gateway(args),
    )
    episodes = service.plan_episodes_from_chapters(
        project,
        parse_comma_separated(args.chapter_ids),
        chapters_per_episode=args.chapters_per_episode,
        tone=args.tone,
        density=args.density,
        use_ai=should_use_ai(args),
    )
    project_service.save_project(project, args.project)
    episode_ids = ", ".join(episode.episode_id for episode in episodes)
    print(f"Planned batch episodes: {len(episodes)} ({episode_ids})")
    return 0


def handle_run_batch_pipeline(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    service = BatchWorkflowService(
        project_service,
        ai_gateway=build_gateway(args),
    )
    episodes = service.run_generation_for_episodes(
        project,
        parse_comma_separated(args.episode_ids),
        tone=args.tone,
        density=args.density,
        style_preset_id=args.style_preset_id,
        use_ai=should_use_ai(args),
        validate=args.validate,
        fail_on_validation_error=args.fail_on_validation_error,
    )
    project_service.save_project(project, args.project)
    output_paths = service.export_episodes(
        project,
        [episode.episode_id for episode in episodes],
        args.output_dir,
        parse_comma_separated(args.export_formats),
    )
    if args.validate:
        issue_count = sum(len(issues) for issues in service.last_validation_issues.values())
        print(f"Validation issues: {issue_count}")
    print(f"Batch pipeline complete: {len(episodes)} episodes, {len(output_paths)} files")
    return 0
