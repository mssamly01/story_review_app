"""Top-level ``story-review`` argparse dispatcher.

Each subcommand registers itself by importing its module and calling
``register(subparsers)``. Keeping this dispatcher tiny means new commands only
have to touch one subcommand module + this file.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from app.cli import (
    batch_cmds,
    bible_cmds,
    export_cmds,
    image_cmds,
    manual_cmds,
    pipeline_cmds,
    project_cmds,
    quality_cmds,
    source_cmds,
)


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

    project_cmds.register(subparsers)
    source_cmds.register(subparsers)
    bible_cmds.register(subparsers)
    pipeline_cmds.register(subparsers)
    export_cmds.register(subparsers)
    image_cmds.register(subparsers)
    quality_cmds.register(subparsers)
    batch_cmds.register(subparsers)
    manual_cmds.register(subparsers)

    return parser
