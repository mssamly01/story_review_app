"""Story-bible subcommands: characters, locations, style presets."""

from __future__ import annotations

import argparse

from app.cli._shared import load_project, parse_comma_separated
from app.domain.character import Character
from app.domain.location import Location
from app.services.bible_service import BibleService
from app.services.project_service import ProjectService


def register(subparsers: argparse._SubParsersAction) -> None:
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
