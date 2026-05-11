"""``add-chapter``, ``parse-story`` — raw source ingestion + parsing."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.cli._shared import add_ai_flags, build_gateway, find_chapter, load_project, should_use_ai
from app.services.project_service import ProjectService
from app.services.source_import_service import SourceImportService
from app.services.story_parser_service import StoryParserService


def register(subparsers: argparse._SubParsersAction) -> None:
    add_chapter = subparsers.add_parser("add-chapter")
    add_chapter.add_argument("--project", required=True)
    add_chapter.add_argument("--title", required=True)
    add_chapter.add_argument("--chapter-number", required=True, type=int)
    add_chapter.add_argument("--text-file", required=True)
    add_chapter.set_defaults(handler=handle_add_chapter)

    parse_story = subparsers.add_parser("parse-story")
    parse_story.add_argument("--project", required=True)
    parse_story.add_argument("--chapter-id", required=True)
    add_ai_flags(parse_story)
    parse_story.set_defaults(handler=handle_parse_story)


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
