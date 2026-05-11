"""Per-episode generation pipeline subcommands:

``plan-episode``, ``generate-beats``, ``rewrite-review``, ``build-prompts``,
``generate-beat-package``, ``run-pipeline``.
"""

from __future__ import annotations

import argparse

from app.cli._shared import (
    add_ai_flags,
    build_gateway,
    find_chapter,
    load_project,
    should_use_ai,
    write_export,
)
from app.services.beat_generator_service import BeatGeneratorService
from app.services.episode_planner_service import EpisodePlannerService
from app.services.project_service import ProjectService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.review_rewriter_service import ReviewRewriterService
from app.services.story_parser_service import StoryParserService


def register(subparsers: argparse._SubParsersAction) -> None:
    plan_episode = subparsers.add_parser("plan-episode")
    plan_episode.add_argument("--project", required=True)
    plan_episode.add_argument("--chapter-id", required=True)
    plan_episode.add_argument("--episode-title", required=True)
    plan_episode.add_argument("--tone", default="mysterious")
    plan_episode.add_argument("--density", default="full")
    add_ai_flags(plan_episode)
    plan_episode.set_defaults(handler=handle_plan_episode)

    generate_beats = subparsers.add_parser("generate-beats")
    generate_beats.add_argument("--project", required=True)
    generate_beats.add_argument("--episode-id", required=True)
    generate_beats.add_argument("--density", default=None)
    add_ai_flags(generate_beats)
    generate_beats.set_defaults(handler=handle_generate_beats)

    rewrite_review = subparsers.add_parser("rewrite-review")
    rewrite_review.add_argument("--project", required=True)
    rewrite_review.add_argument("--episode-id", required=True)
    rewrite_review.add_argument("--tone", default=None)
    rewrite_review.add_argument("--density", default=None)
    add_ai_flags(rewrite_review)
    rewrite_review.set_defaults(handler=handle_rewrite_review)

    build_prompts = subparsers.add_parser("build-prompts")
    build_prompts.add_argument("--project", required=True)
    build_prompts.add_argument("--episode-id", required=True)
    build_prompts.add_argument("--style-preset-id", default=None)
    add_ai_flags(build_prompts)
    build_prompts.set_defaults(handler=handle_build_prompts)

    generate_beat_package = subparsers.add_parser("generate-beat-package")
    generate_beat_package.add_argument("--project", required=True)
    generate_beat_package.add_argument("--episode-id", required=True)
    generate_beat_package.add_argument("--scene-id", default=None)
    generate_beat_package.add_argument("--tone", default=None)
    generate_beat_package.add_argument("--density", default=None)
    generate_beat_package.add_argument("--style-preset-id", default=None)
    add_ai_flags(generate_beat_package)
    generate_beat_package.set_defaults(handler=handle_generate_beat_package)

    pipeline = subparsers.add_parser("run-pipeline")
    pipeline.add_argument("--project", required=True)
    pipeline.add_argument("--chapter-id", required=True)
    pipeline.add_argument("--episode-title", required=True)
    pipeline.add_argument("--output", required=True)
    pipeline.add_argument("--tone", default="mysterious")
    pipeline.add_argument("--density", default="full")
    pipeline.add_argument("--style-preset-id", default=None)
    pipeline.add_argument("--export-format", default="markdown")
    add_ai_flags(pipeline)
    pipeline.set_defaults(handler=handle_run_pipeline)


def handle_plan_episode(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    episode = EpisodePlannerService(
        project_service,
        ai_gateway=build_gateway(args),
        use_ai=should_use_ai(args),
    ).plan_episode(
        project,
        selected_source_chapter_ids=[args.chapter_id],
        narration_style=args.tone,
        retelling_density=args.density,
        episode_title=args.episode_title,
    )
    project_service.save_project(project, args.project)
    print(f"Planned episode: {episode.episode_id}")
    return 0


def handle_generate_beats(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    beats = BeatGeneratorService(
        project_service,
        ai_gateway=build_gateway(args),
        use_ai=should_use_ai(args),
    ).generate_beats_for_episode(
        project,
        args.episode_id,
        retelling_density=args.density,
    )
    project_service.save_project(project, args.project)
    print(f"Generated beats: {len(beats)}")
    return 0


def handle_rewrite_review(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    beats = ReviewRewriterService(
        ai_gateway=build_gateway(args),
        use_ai=should_use_ai(args),
    ).rewrite_episode(
        project,
        args.episode_id,
        narration_style=args.tone,
        retelling_density=args.density,
    )
    project_service.save_project(project, args.project)
    print(f"Rewrote beats: {len(beats)}")
    return 0


def handle_build_prompts(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    beats = PromptBuilderService(
        ai_gateway=build_gateway(args),
        use_ai=should_use_ai(args),
    ).build_prompts_for_episode(
        project,
        args.episode_id,
        style_preset_id=args.style_preset_id,
    )
    project_service.save_project(project, args.project)
    print(f"Built prompts: {len(beats)}")
    return 0


def handle_generate_beat_package(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    gateway = build_gateway(args)
    service = BeatGeneratorService(
        project_service=project_service,
        ai_gateway=gateway,
    )
    if args.scene_id:
        beats = service.generate_unified_package_for_scene(
            project,
            args.episode_id,
            args.scene_id,
            narration_style=args.tone,
            retelling_density=args.density,
            style_preset_id=args.style_preset_id,
            use_ai=should_use_ai(args),
        )
    else:
        beats = service.generate_unified_package_for_episode(
            project,
            args.episode_id,
            narration_style=args.tone,
            retelling_density=args.density,
            style_preset_id=args.style_preset_id,
            use_ai=should_use_ai(args),
        )
    project_service.save_project(project, args.project)
    print(f"Generated unified beat package: {len(beats)} beats.")
    return 0


def handle_run_pipeline(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    chapter = find_chapter(project, args.chapter_id)
    gateway = build_gateway(args)
    use_ai = should_use_ai(args)

    StoryParserService(ai_gateway=gateway, use_ai=use_ai).parse(chapter)
    episode = EpisodePlannerService(
        project_service,
        ai_gateway=gateway,
        use_ai=use_ai,
    ).plan_episode(
        project,
        selected_source_chapter_ids=[args.chapter_id],
        narration_style=args.tone,
        retelling_density=args.density,
        episode_title=args.episode_title,
    )
    BeatGeneratorService(
        project_service,
        ai_gateway=gateway,
        use_ai=use_ai,
    ).generate_beats_for_episode(
        project,
        episode.episode_id,
        retelling_density=args.density,
    )
    ReviewRewriterService(
        ai_gateway=gateway,
        use_ai=use_ai,
    ).rewrite_episode(
        project,
        episode.episode_id,
        narration_style=args.tone,
        retelling_density=args.density,
    )
    PromptBuilderService(
        ai_gateway=gateway,
        use_ai=use_ai,
    ).build_prompts_for_episode(
        project,
        episode.episode_id,
        style_preset_id=args.style_preset_id,
    )

    project_service.save_project(project, args.project)
    write_export(
        project_service,
        project,
        episode.episode_id,
        args.export_format,
        args.output,
    )
    print(f"Pipeline complete: {episode.episode_id}")
    return 0
