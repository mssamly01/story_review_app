"""``import-image``, ``select-image``, ``list-images`` — beat image attachments."""

from __future__ import annotations

import argparse

from app.cli._shared import load_project
from app.services.beat_image_service import BeatImageService
from app.services.project_service import ProjectService


def register(subparsers: argparse._SubParsersAction) -> None:
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
