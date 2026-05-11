"""``export-prompt``, ``import-ai-result`` — manual AI workflow.

Lets users copy prompts into an external AI (ChatGPT, Claude) and paste the
result back into the project without wiring a real ``AIGateway``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.cli._shared import load_project
from app.services.manual_ai_service import SUPPORTED_STEPS, ManualAIService
from app.services.project_service import ProjectService


def register(subparsers: argparse._SubParsersAction) -> None:
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
        content = service.format_prompt_for_clipboard(exported)
        output_path.write_text(content, encoding="utf-8")
    else:
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
