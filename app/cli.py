"""Command-line workflow for project JSON files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from app.controllers.export_profile_controller import ExportProfileController
from app.controllers.onboarding_controller import OnboardingController
from app.controllers.production_readiness_controller import (
    ProductionReadinessController,
)
from app.controllers.prompt_quality_controller import PromptQualityController
from app.controllers.repair_controller import RepairController
from app.controllers.validation_controller import ValidationController
from app.domain.character import Character
from app.domain.location import Location
from app.domain.project import Project
from app.infrastructure.ai_gateway import AIGateway
from app.infrastructure.ai_gateway_factory import create_ai_gateway
from app.services.batch_workflow_service import BatchWorkflowService
from app.services.beat_generator_service import BeatGeneratorService
from app.services.beat_image_service import BeatImageService
from app.services.bible_service import BibleService
from app.services.episode_planner_service import EpisodePlannerService
from app.services.export_service import ExportService
from app.services.manual_ai_service import SUPPORTED_STEPS, ManualAIService
from app.services.project_service import ProjectService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.review_rewriter_service import ReviewRewriterService
from app.services.source_import_service import SourceImportService
from app.services.story_parser_service import StoryParserService


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    try:
        return args.handler(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="story-review",
        description="Manage comic-style story review projects.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create-project")
    create.add_argument("--title", required=True)
    create.add_argument("--output", required=True)
    create.add_argument("--genre", default="")
    create.add_argument("--language", default="vi")
    create.add_argument("--default-narration-style", default="mysterious")
    create.add_argument("--default-art-style", default="dark fantasy webtoon")
    create.set_defaults(handler=handle_create_project)

    list_templates = subparsers.add_parser("list-templates")
    list_templates.set_defaults(handler=handle_list_templates)

    create_from_template = subparsers.add_parser("create-project-from-template")
    create_from_template.add_argument("--template", required=True)
    create_from_template.add_argument("--title", required=True)
    create_from_template.add_argument("--output", required=True)
    create_from_template.add_argument("--language", default=None)
    create_from_template.add_argument("--project-id", default=None)
    create_from_template.set_defaults(handler=handle_create_project_from_template)

    apply_template = subparsers.add_parser("apply-template")
    apply_template.add_argument("--project", required=True)
    apply_template.add_argument("--template", required=True)
    apply_template.add_argument("--overwrite-existing-styles", action="store_true")
    apply_template.set_defaults(handler=handle_apply_template)

    add_chapter = subparsers.add_parser("add-chapter")
    add_chapter.add_argument("--project", required=True)
    add_chapter.add_argument("--title", required=True)
    add_chapter.add_argument("--chapter-number", required=True, type=int)
    add_chapter.add_argument("--text-file", required=True)
    add_chapter.set_defaults(handler=handle_add_chapter)

    list_styles = subparsers.add_parser("list-style-presets")
    list_styles.add_argument("--project", required=True)
    list_styles.set_defaults(handler=handle_list_style_presets)

    create_styles = subparsers.add_parser("create-default-style-presets")
    create_styles.add_argument("--project", required=True)
    create_styles.set_defaults(handler=handle_create_default_style_presets)

    add_character = subparsers.add_parser("add-character")
    add_character.add_argument("--project", required=True)
    add_character.add_argument("--id", required=True)
    add_character.add_argument("--name", required=True)
    add_character.add_argument("--aliases", default="")
    add_character.add_argument("--role", default="")
    add_character.add_argument("--appearance", default="")
    add_character.add_argument("--default-outfit", default="")
    add_character.add_argument("--visual-prompt-base", default="")
    add_character.add_argument("--negative-prompt-terms", default="")
    add_character.set_defaults(handler=handle_add_character)

    add_location = subparsers.add_parser("add-location")
    add_location.add_argument("--project", required=True)
    add_location.add_argument("--id", required=True)
    add_location.add_argument("--name", required=True)
    add_location.add_argument("--aliases", default="")
    add_location.add_argument("--description", default="")
    add_location.add_argument("--mood", default="")
    add_location.add_argument("--lighting", default="")
    add_location.add_argument("--visual-prompt-base", default="")
    add_location.add_argument("--recurring-props", default="")
    add_location.add_argument("--negative-prompt-terms", default="")
    add_location.set_defaults(handler=handle_add_location)

    parse_story = subparsers.add_parser("parse-story")
    parse_story.add_argument("--project", required=True)
    parse_story.add_argument("--chapter-id", required=True)
    add_ai_flags(parse_story)
    parse_story.set_defaults(handler=handle_parse_story)

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

    export = subparsers.add_parser("export")
    export.add_argument("--project", required=True)
    export.add_argument("--episode-id", required=True)
    export.add_argument("--format", required=True)
    export.add_argument("--output", required=True)
    export.set_defaults(handler=handle_export)

    import_image = subparsers.add_parser(
        "import-image",
        help="Attach an externally-rendered image file to a beat.",
    )
    import_image.add_argument("--project", required=True)
    import_image.add_argument("--beat-id", required=True)
    import_image.add_argument("--path", required=True)
    import_image.add_argument("--model", default="")
    import_image.add_argument("--seed", default="")
    import_image.add_argument("--notes", default="")
    import_image.add_argument(
        "--no-select",
        action="store_true",
        help="Attach without marking this variant as selected.",
    )
    import_image.set_defaults(handler=handle_import_image)

    select_image = subparsers.add_parser(
        "select-image",
        help="Mark an attached image variant as the selected one for its beat.",
    )
    select_image.add_argument("--project", required=True)
    select_image.add_argument("--beat-id", required=True)
    select_image.add_argument("--image-id", required=True)
    select_image.set_defaults(handler=handle_select_image)

    list_images = subparsers.add_parser(
        "list-images",
        help="List all image variants attached to a beat.",
    )
    list_images.add_argument("--project", required=True)
    list_images.add_argument("--beat-id", required=True)
    list_images.set_defaults(handler=handle_list_images)

    list_export_profiles = subparsers.add_parser("list-export-profiles")
    list_export_profiles.set_defaults(handler=handle_list_export_profiles)

    export_profile = subparsers.add_parser("export-profile")
    export_profile.add_argument("--project", required=True)
    export_profile.add_argument("--episode-id", required=True)
    export_profile.add_argument("--profile", required=True)
    export_profile.add_argument("--output-dir", required=True)
    export_profile.set_defaults(handler=handle_export_profile)

    batch_export_profile = subparsers.add_parser("batch-export-profile")
    batch_export_profile.add_argument("--project", required=True)
    batch_export_profile.add_argument("--episode-ids", required=True)
    batch_export_profile.add_argument("--profile", required=True)
    batch_export_profile.add_argument("--output-dir", required=True)
    batch_export_profile.set_defaults(handler=handle_batch_export_profile)

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

    # ── Manual AI workflow ───────────────────────────────────────
    export_prompt = subparsers.add_parser(
        "export-prompt",
        help="Export AI prompt for a pipeline step to paste into ChatGPT/Claude.",
    )
    export_prompt.add_argument("--project", required=True)
    export_prompt.add_argument(
        "--step",
        required=True,
        choices=SUPPORTED_STEPS,
        help="Pipeline step: parse-story, plan-episode, generate-beats, "
        "rewrite-review, build-prompts",
    )
    export_prompt.add_argument("--chapter-id", default=None)
    export_prompt.add_argument("--episode-id", default=None)
    export_prompt.add_argument("--tone", default=None)
    export_prompt.add_argument("--density", default=None)
    export_prompt.add_argument("--style-preset-id", default=None)
    export_prompt.add_argument("--output", required=True, help="Output file (.json or .md)")
    export_prompt.set_defaults(handler=handle_export_prompt)

    import_result = subparsers.add_parser(
        "import-ai-result",
        help="Import AI JSON result from file and apply to project.",
    )
    import_result.add_argument("--project", required=True)
    import_result.add_argument(
        "--step",
        required=True,
        choices=SUPPORTED_STEPS,
    )
    import_result.add_argument(
        "--result-file", required=True, help="Path to JSON file with AI result."
    )
    import_result.add_argument("--chapter-id", default=None)
    import_result.add_argument("--episode-id", default=None)
    import_result.add_argument("--tone", default=None)
    import_result.add_argument("--density", default=None)
    import_result.add_argument("--style-preset-id", default=None)
    import_result.set_defaults(handler=handle_import_ai_result)

    return parser


def add_ai_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--use-ai", action="store_true")
    parser.add_argument("--mock-ai", action="store_true")
    parser.add_argument("--real-ai", action="store_true")
    parser.add_argument("--model", default=None)


def handle_create_project(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = project_service.create_project(
        args.title,
        genre=args.genre,
        language=args.language,
        default_narration_style=args.default_narration_style,
        default_art_style=args.default_art_style,
    )
    project_service.save_project(project, args.output)
    print(f"Created project: {project.title}")
    return 0


def handle_list_templates(args: argparse.Namespace) -> int:
    del args
    templates = OnboardingController().list_templates()
    for template in templates:
        print(
            f"{template.template_id}: {template.name} "
            f"(genre={template.genre}, "
            f"tone={template.default_narration_style}, "
            f"density={template.default_retelling_density})"
        )
    return 0


def handle_create_project_from_template(args: argparse.Namespace) -> int:
    project = OnboardingController().create_project(
        args.template,
        args.title,
        args.output,
        project_id=args.project_id,
        language=args.language,
    )
    print(f"Created project from template: {project.title} " f"({args.template})")
    return 0


def handle_apply_template(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    OnboardingController(project_service).apply_template(
        project,
        args.template,
        overwrite_existing_styles=args.overwrite_existing_styles,
    )
    project_service.save_project(project, args.project)
    print(f"Applied template: {args.template}")
    return 0


def handle_add_chapter(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    raw_text = Path(args.text_file).read_text(encoding="utf-8")
    chapter = SourceImportService(project_service).import_raw_text(
        project,
        title=args.title,
        chapter_number=args.chapter_number,
        raw_text=raw_text,
    )
    project_service.save_project(project, args.project)
    print(f"Added chapter: {chapter.chapter_id}")
    return 0


def handle_list_style_presets(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    if not project.style_presets:
        print("No style presets found.")
        return 0
    for style in project.style_presets:
        print(f"{style.style_id}: {style.name}")
    return 0


def handle_create_default_style_presets(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    presets = BibleService().create_default_style_presets(project)
    project_service.save_project(project, args.project)
    print(f"Created default style presets: {len(presets)}")
    return 0


def handle_add_character(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    character = Character(
        character_id=args.id,
        name=args.name,
        aliases=parse_comma_separated(args.aliases),
        role=args.role,
        appearance=args.appearance,
        default_outfit=args.default_outfit,
        visual_prompt_base=args.visual_prompt_base,
        negative_prompt_terms=parse_comma_separated(args.negative_prompt_terms),
    )
    BibleService().add_or_update_character(project, character)
    project_service.save_project(project, args.project)
    print(f"Saved character: {character.character_id}")
    return 0


def handle_add_location(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    location = Location(
        location_id=args.id,
        name=args.name,
        aliases=parse_comma_separated(args.aliases),
        description=args.description,
        mood=args.mood,
        lighting=args.lighting,
        visual_prompt_base=args.visual_prompt_base,
        recurring_props=parse_comma_separated(args.recurring_props),
        negative_prompt_terms=parse_comma_separated(args.negative_prompt_terms),
    )
    BibleService().add_or_update_location(project, location)
    project_service.save_project(project, args.project)
    print(f"Saved location: {location.location_id}")
    return 0


def handle_parse_story(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    chapter = find_chapter(project, args.chapter_id)
    parser = StoryParserService(
        ai_gateway=build_gateway(args),
        use_ai=should_use_ai(args),
    )
    result = parser.parse(chapter)
    print(
        "Parsed chapter: "
        f"{result.chapter_id} "
        f"({len(result.scene_candidates)} scenes, "
        f"{len(result.important_events)} events)"
    )
    return 0


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


def handle_export(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    write_export(project_service, project, args.episode_id, args.format, args.output)
    print(f"Exported {args.format}: {args.output}")
    return 0


def handle_import_image(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    variant = BeatImageService(project_service).attach_image(
        project,
        args.beat_id,
        args.path,
        model=args.model,
        seed=args.seed,
        notes=args.notes,
        select=not args.no_select,
    )
    project_service.save_project(project, args.project)
    print(
        f"Attached image {variant.image_id} to beat {args.beat_id}: "
        f"{variant.image_path}" + (" [selected]" if variant.selected else "")
    )
    return 0


def handle_select_image(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    variant = BeatImageService(project_service).select_image(project, args.beat_id, args.image_id)
    project_service.save_project(project, args.project)
    print(f"Selected image {variant.image_id} for beat {args.beat_id}.")
    return 0


def handle_list_images(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    variants = BeatImageService(project_service).list_images(project, args.beat_id)
    if not variants:
        print(f"(no images attached to beat {args.beat_id})")
        return 0
    for variant in variants:
        marker = "*" if variant.selected else "-"
        meta = " ".join(
            part
            for part in (
                f"model={variant.model}" if variant.model else "",
                f"seed={variant.seed}" if variant.seed else "",
                f"at={variant.generated_at}" if variant.generated_at else "",
            )
            if part
        )
        print(f"{marker} {variant.image_id}  {variant.image_path}  {meta}")
    return 0


def handle_list_export_profiles(args: argparse.Namespace) -> int:
    del args
    for profile in ExportProfileController().list_profiles():
        print(f"{profile.profile_id}: {profile.name} " f"({', '.join(profile.formats)})")
    return 0


def handle_export_profile(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    paths = ExportProfileController(project_service).export_episode_with_profile(
        project,
        args.episode_id,
        args.profile,
        args.output_dir,
    )
    for path in paths:
        print(path)
    return 0


def handle_batch_export_profile(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    paths = ExportProfileController(project_service).export_batch_with_profile(
        project,
        parse_comma_separated(args.episode_ids),
        args.profile,
        args.output_dir,
    )
    for path in paths:
        print(path)
    return 0


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


def handle_export_prompt(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    service = ManualAIService(project_service)

    exported = service.export_prompt(
        project,
        step=args.step,
        chapter_id=args.chapter_id,
        episode_id=args.episode_id,
        tone=args.tone,
        density=args.density,
        style_preset_id=args.style_preset_id,
    )

    output_path = Path(args.output)
    if output_path.suffix == ".md":
        # Xuất dạng markdown — sẵn sàng copy-paste vào AI chat
        content = service.format_prompt_for_clipboard(exported)
        output_path.write_text(content, encoding="utf-8")
    else:
        # Xuất dạng JSON — chứa cả metadata
        content = json.dumps(exported, ensure_ascii=False, indent=2)
        output_path.write_text(content, encoding="utf-8")

    print(f"Exported prompt for step '{args.step}': {output_path}")
    return 0


def handle_import_ai_result(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    service = ManualAIService(project_service)

    result_path = Path(args.result_file)
    if not result_path.exists():
        raise FileNotFoundError(f"Result file not found: {result_path}")

    result_data = json.loads(result_path.read_text(encoding="utf-8"))

    message = service.import_result(
        project,
        step=args.step,
        result_data=result_data,
        chapter_id=args.chapter_id,
        episode_id=args.episode_id,
        tone=args.tone,
        density=args.density,
        style_preset_id=args.style_preset_id,
    )

    project_service.save_project(project, args.project)
    print(message)
    return 0


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


if __name__ == "__main__":
    raise SystemExit(main())
