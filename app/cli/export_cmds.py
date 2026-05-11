"""``export``, ``list-export-profiles``, ``export-profile``,
``batch-export-profile`` — per-episode and per-profile export."""

from __future__ import annotations

import argparse

from app.cli._shared import load_project, parse_comma_separated, write_export
from app.controllers.export_profile_controller import ExportProfileController
from app.services.project_service import ProjectService


def register(subparsers: argparse._SubParsersAction) -> None:
    export = subparsers.add_parser("export")
    export.add_argument("--project", required=True)
    export.add_argument("--episode-id", required=True)
    export.add_argument("--format", required=True)
    export.add_argument("--output", required=True)
    export.set_defaults(handler=handle_export)

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


def handle_export(args: argparse.Namespace) -> int:
    project_service = ProjectService()
    project = load_project(project_service, args.project)
    write_export(project_service, project, args.episode_id, args.format, args.output)
    print(f"Exported {args.format}: {args.output}")
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
