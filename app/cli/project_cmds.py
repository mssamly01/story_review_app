"""``create-project``, ``list-templates``, ``create-project-from-template``,
``apply-template`` — project lifecycle subcommands."""

from __future__ import annotations

import argparse

from app.cli._shared import load_project
from app.controllers.onboarding_controller import OnboardingController
from app.services.project_service import ProjectService


def register(subparsers: argparse._SubParsersAction) -> None:
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
