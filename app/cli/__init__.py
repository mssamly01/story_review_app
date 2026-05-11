"""Command-line workflow for project JSON files.

Public surface kept stable for callers that previously did ``from app import
cli; cli.main(...)`` — the dispatcher and shared helpers are re-exported here
so test files and integrations don't have to update their imports.
"""

from __future__ import annotations

from app.cli._main import build_parser, main
from app.cli._shared import (
    add_ai_flags,
    build_gateway,
    find_chapter,
    format_batch_readiness_report,
    format_prompt_quality_report,
    format_readiness_report,
    format_repair_actions_markdown,
    format_repair_actions_text,
    format_repair_results_text,
    format_validation_issues,
    load_project,
    parse_comma_separated,
    should_use_ai,
    write_export,
)

__all__ = [
    "main",
    "build_parser",
    "add_ai_flags",
    "build_gateway",
    "find_chapter",
    "format_batch_readiness_report",
    "format_prompt_quality_report",
    "format_readiness_report",
    "format_repair_actions_markdown",
    "format_repair_actions_text",
    "format_repair_results_text",
    "format_validation_issues",
    "load_project",
    "parse_comma_separated",
    "should_use_ai",
    "write_export",
]


if __name__ == "__main__":
    import sys

    sys.exit(main())
