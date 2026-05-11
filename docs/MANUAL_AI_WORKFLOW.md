# Manual AI Workflow — Hướng dẫn Vibe Code

> Tính năng cho phép **lấy prompt ra ngoài** (ChatGPT, Claude, Gemini...) → **AI xử lý** → **dán kết quả JSON lại vào app**.

---

## Mục lục

1. [Tổng quan kiến trúc](#1-tổng-quan-kiến-trúc)
2. [Luồng hoạt động](#2-luồng-hoạt-động)
3. [Danh sách files cần tạo/sửa](#3-danh-sách-files-cần-tạosửa)
4. [Code chi tiết](#4-code-chi-tiết)
   - 4.1 [ManualAIService](#41-manualaiservice)
   - 4.2 [CLI commands](#42-cli-commands)
   - 4.3 [GUI — PySide6 UI](#43-gui--pyside6-ui)
5. [Output schema cho từng bước](#5-output-schema-cho-từng-bước)
6. [Ví dụ sử dụng end-to-end](#6-ví-dụ-sử-dụng-end-to-end)
7. [Test plan](#7-test-plan)

---

## 1. Tổng quan kiến trúc

App hiện tại có 5 bước pipeline, mỗi bước gọi AI qua `AIGateway`:

```
SourceChapter
  → [1] parse-story          (StoryParserService)
  → [2] plan-episode          (EpisodePlannerService)
  → [3] generate-beats        (BeatGeneratorService)
  → [4] rewrite-review        (ReviewRewriterService)
  → [5] build-prompts         (PromptBuilderService)
  → Export
```

Mỗi bước đều gọi `ai_gateway.generate_json(prompt_name, input_data)`:
- `prompt_name` = tên file prompt trong `app/prompts/` (ví dụ: `"story_parser"`)
- `input_data` = dict chứa dữ liệu đầu vào (chapter text, scene, beat, bible...)

**Ý tưởng**: Thay vì gọi AI Gateway, ta **xuất prompt + input_data ra file** → user copy vào ChatGPT → lấy JSON về → **import lại vào app**.

### Luồng kiến trúc tuân thủ AGENTS.md

```
UI → Controller → ManualAIService → (export file / import file)
                                   ↘ Service._*_from_ai_response()
```

Không vi phạm Rule 4 (UI không gọi AI trực tiếp) vì user là người gọi AI bên ngoài.

---

## 2. Luồng hoạt động

### Export Prompt (lấy prompt ra)

```
User click "Export Prompt"
  → ManualAIService.export_prompt(project, step, ...)
  → Đọc prompt template từ app/prompts/{step}_prompt.md
  → Build input_data dict (giống hệt cách service build cho AI)
  → Gộp thành 1 file JSON/MD:
      {
        "step": "parse-story",
        "prompt_template": "# Story Parser Prompt\n...",
        "input_data": { ... },
        "expected_output_schema": { ... }
      }
  → User mở file → copy nội dung → paste vào ChatGPT/Claude
```

### Import Result (dán kết quả lại)

```
User lấy JSON result từ AI
  → Lưu vào file .json
  → Click "Import AI Result" hoặc chạy CLI
  → ManualAIService.import_result(project, step, result_json)
  → Dùng đúng hàm _*_from_ai_response() của service gốc
  → Cập nhật project
  → Save project
```

---

## 3. Danh sách files cần tạo/sửa

### Files mới cần tạo

| File | Mô tả |
|------|--------|
| `app/services/manual_ai_service.py` | Service chính: export prompt, import result |
| `tests/test_manual_ai_service.py` | Unit tests |

### Files cần sửa

| File | Thay đổi |
|------|----------|
| `app/cli.py` | Thêm 2 subcommands: `export-prompt`, `import-ai-result` |
| `app/controllers/generation_controller.py` | Thêm methods gọi ManualAIService |
| `app/ui/main_window.py` | Thêm 2 buttons: "Export Prompt", "Import AI Result" |
| `app/ui/episode_panel.py` | Thêm dropdown chọn pipeline step |

---

## 4. Code chi tiết

### 4.1 ManualAIService

Tạo file `app/services/manual_ai_service.py`:

```python
"""Service cho manual AI workflow: export prompts và import results.

Cho phép user copy prompt ra ChatGPT/Claude, lấy JSON result, dán lại vào app.
"""

from __future__ import annotations

import json
from typing import Any

from app.domain.project import Project
from app.domain.source_chapter import SourceChapter
from app.infrastructure.prompt_template_loader import PromptTemplateLoader
from app.services.beat_generator_service import BeatGeneratorService
from app.services.episode_planner_service import EpisodePlannerService
from app.services.project_service import ProjectService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.review_rewriter_service import ReviewRewriterService
from app.services.story_parser_service import StoryParserService


SUPPORTED_STEPS = [
    "parse-story",
    "plan-episode",
    "generate-beats",
    "rewrite-review",
    "build-prompts",
]

_STEP_TO_PROMPT_NAME = {
    "parse-story": "story_parser",
    "plan-episode": "episode_planner",
    "generate-beats": "beat_generator",
    "rewrite-review": "review_rewriter",
    "build-prompts": "image_prompt_builder",
}


class ManualAIService:
    """Xuất prompt cho user copy ra AI bên ngoài, import kết quả JSON lại."""

    def __init__(
        self,
        project_service: ProjectService | None = None,
    ) -> None:
        self.project_service = project_service or ProjectService()
        self.prompt_loader = PromptTemplateLoader()

    # ── Export ────────────────────────────────────────────────────

    def export_prompt(
        self,
        project: Project,
        *,
        step: str,
        chapter_id: str | None = None,
        episode_id: str | None = None,
        tone: str | None = None,
        density: str | None = None,
        style_preset_id: str | None = None,
    ) -> dict[str, Any]:
        """Trả về dict chứa prompt_template + input_data + output_schema."""
        self._validate_step(step)
        prompt_name = _STEP_TO_PROMPT_NAME[step]
        template_text = self.prompt_loader.load(prompt_name)

        input_data = self._build_input_data(
            project,
            step=step,
            chapter_id=chapter_id,
            episode_id=episode_id,
            tone=tone,
            density=density,
            style_preset_id=style_preset_id,
        )

        return {
            "step": step,
            "prompt_name": prompt_name,
            "instructions": (
                "Copy toàn bộ nội dung bên dưới vào ChatGPT/Claude/Gemini.\n"
                "AI sẽ trả về JSON theo output schema.\n"
                "Lưu JSON đó vào file .json rồi dùng lệnh import-ai-result."
            ),
            "prompt_template": template_text,
            "input_data": input_data,
        }

    def format_prompt_for_clipboard(
        self,
        exported: dict[str, Any],
    ) -> str:
        """Tạo chuỗi text sẵn sàng paste vào AI chat."""
        template = exported["prompt_template"]
        payload = json.dumps(
            exported["input_data"],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        return f"{template.rstrip()}\n\n## Runtime input\n```json\n{payload}\n```"

    # ── Import ───────────────────────────────────────────────────

    def import_result(
        self,
        project: Project,
        *,
        step: str,
        result_data: dict[str, Any],
        chapter_id: str | None = None,
        episode_id: str | None = None,
        tone: str | None = None,
        density: str | None = None,
        style_preset_id: str | None = None,
    ) -> str:
        """Áp dụng AI result vào project. Trả về summary message."""
        self._validate_step(step)

        if step == "parse-story":
            return self._import_parse(project, result_data, chapter_id)
        if step == "plan-episode":
            return self._import_plan(
                project, result_data, chapter_id, tone, density,
            )
        if step == "generate-beats":
            return self._import_beats(project, result_data, episode_id, density)
        if step == "rewrite-review":
            return self._import_rewrite(
                project, result_data, episode_id, tone, density,
            )
        if step == "build-prompts":
            return self._import_prompts(
                project, result_data, episode_id, style_preset_id,
            )
        raise ValueError(f"Unsupported step: {step}")

    # ── Build input_data (giống hệt cách các service build) ─────

    def _build_input_data(
        self,
        project: Project,
        *,
        step: str,
        chapter_id: str | None,
        episode_id: str | None,
        tone: str | None,
        density: str | None,
        style_preset_id: str | None,
    ) -> dict[str, Any]:
        if step == "parse-story":
            return self._input_parse(project, chapter_id)
        if step == "plan-episode":
            return self._input_plan(project, chapter_id, tone, density)
        if step == "generate-beats":
            return self._input_beats(project, episode_id, density)
        if step == "rewrite-review":
            return self._input_rewrite(project, episode_id, tone, density)
        if step == "build-prompts":
            return self._input_prompts(project, episode_id, style_preset_id)
        raise ValueError(f"Unsupported step: {step}")

    def _input_parse(
        self, project: Project, chapter_id: str | None,
    ) -> dict[str, Any]:
        chapter = self._require_chapter(project, chapter_id)
        return {
            "project_context": {
                "title": project.title,
                "genre": project.genre,
                "language": project.language,
                "narration_style": project.default_narration_style,
                "retelling_density": project.retelling_density,
            },
            "chapter_id": chapter.chapter_id,
            "chapter_title": chapter.title,
            "chapter_number": chapter.chapter_number,
            "source_text": chapter.raw_text,
            "character_bible": [c.to_dict() for c in project.characters],
            "location_bible": [loc.to_dict() for loc in project.locations],
            "notes": chapter.notes,
        }

    def _input_plan(
        self,
        project: Project,
        chapter_id: str | None,
        tone: str | None,
        density: str | None,
    ) -> dict[str, Any]:
        chapter = self._require_chapter(project, chapter_id)
        return {
            "project_context": {
                "title": project.title,
                "genre": project.genre,
                "language": project.language,
            },
            "source_chapter_ids": [chapter.chapter_id],
            "source_chapters": [
                {
                    "chapter_id": chapter.chapter_id,
                    "title": chapter.title,
                    "chapter_number": chapter.chapter_number,
                    "raw_text": chapter.raw_text,
                    "notes": chapter.notes,
                }
            ],
            "narration_style": tone or project.default_narration_style,
            "retelling_density": density or project.retelling_density,
            "character_bible": [c.to_dict() for c in project.characters],
            "location_bible": [loc.to_dict() for loc in project.locations],
        }

    def _input_beats(
        self,
        project: Project,
        episode_id: str | None,
        density: str | None,
    ) -> dict[str, Any]:
        episode = self._require_episode(project, episode_id)
        source_chapters = self._chapters_for_episode(
            project, episode.source_chapter_ids,
        )
        scenes_input = []
        for scene in episode.scenes:
            scenes_input.append({
                "episode_id": episode.episode_id,
                "scene_id": scene.scene_id,
                "scene": scene.to_dict(),
                "source_chapter_context": [
                    {
                        "chapter_id": ch.chapter_id,
                        "title": ch.title,
                        "raw_text": ch.raw_text,
                    }
                    for ch in source_chapters
                ],
                "retelling_density": density or episode.density,
                "character_bible": [c.to_dict() for c in project.characters],
                "location_bible": [loc.to_dict() for loc in project.locations],
            })
        return {
            "episode_id": episode.episode_id,
            "scenes": scenes_input,
        }

    def _input_rewrite(
        self,
        project: Project,
        episode_id: str | None,
        tone: str | None,
        density: str | None,
    ) -> dict[str, Any]:
        episode = self._require_episode(project, episode_id)
        source_chapters = self._chapters_for_episode(
            project, episode.source_chapter_ids,
        )
        beats_input = []
        for scene in episode.scenes:
            for beat in scene.ordered_beats():
                beats_input.append({
                    "episode": episode.to_dict(),
                    "scene": scene.to_dict(),
                    "beat": beat.to_dict(),
                    "beat_id": beat.beat_id,
                    "source_chapter_context": [
                        ch.to_dict() for ch in source_chapters
                    ],
                    "narration_style": tone or episode.tone,
                    "retelling_density": density or episode.density,
                })
        return {
            "episode_id": episode.episode_id,
            "beats": beats_input,
        }

    def _input_prompts(
        self,
        project: Project,
        episode_id: str | None,
        style_preset_id: str | None,
    ) -> dict[str, Any]:
        episode = self._require_episode(project, episode_id)
        style_preset = self._find_style_preset(project, style_preset_id)

        beats_input = []
        for scene in episode.scenes:
            for beat in scene.ordered_beats():
                beats_input.append({
                    "episode": episode.to_dict(),
                    "scene": scene.to_dict(),
                    "beat": beat.to_dict(),
                    "beat_id": beat.beat_id,
                    "character_bible": [
                        c.to_dict() for c in project.characters
                    ],
                    "location_bible": [
                        loc.to_dict() for loc in project.locations
                    ],
                    "style_preset": (
                        style_preset.to_dict() if style_preset else {}
                    ),
                })
        return {
            "episode_id": episode.episode_id,
            "beats": beats_input,
        }

    # ── Import handlers ──────────────────────────────────────────

    def _import_parse(
        self,
        project: Project,
        result_data: dict[str, Any],
        chapter_id: str | None,
    ) -> str:
        chapter = self._require_chapter(project, chapter_id)
        parser = StoryParserService(use_ai=False)
        parsed = parser._parsed_result_from_ai_response(
            source_chapter=chapter,
            response=result_data,
        )
        return (
            f"Imported parse result: {parsed.chapter_id} — "
            f"{len(parsed.scene_candidates)} scenes, "
            f"{len(parsed.important_events)} events"
        )

    def _import_plan(
        self,
        project: Project,
        result_data: dict[str, Any],
        chapter_id: str | None,
        tone: str | None,
        density: str | None,
    ) -> str:
        chapter = self._require_chapter(project, chapter_id)
        gateway = _SingleResponseGateway(result_data)
        planner = EpisodePlannerService(
            self.project_service,
            ai_gateway=gateway,
            use_ai=True,
        )
        episode = planner.plan_episode(
            project,
            selected_source_chapter_ids=[chapter.chapter_id],
            narration_style=tone or project.default_narration_style,
            retelling_density=density or project.retelling_density,
        )
        return (
            f"Imported episode: {episode.episode_id} "
            f"({len(episode.scenes)} scenes)"
        )

    def _import_beats(
        self,
        project: Project,
        result_data: dict[str, Any],
        episode_id: str | None,
        density: str | None,
    ) -> str:
        episode = self._require_episode(project, episode_id)
        gateway = _SingleResponseGateway(result_data)
        generator = BeatGeneratorService(
            self.project_service,
            ai_gateway=gateway,
            use_ai=True,
        )
        beats = generator.generate_beats_for_episode(
            project,
            episode.episode_id,
            retelling_density=density,
        )
        return f"Imported {len(beats)} beats"

    def _import_rewrite(
        self,
        project: Project,
        result_data: dict[str, Any],
        episode_id: str | None,
        tone: str | None,
        density: str | None,
    ) -> str:
        episode = self._require_episode(project, episode_id)
        gateway = _SingleResponseGateway(result_data)
        rewriter = ReviewRewriterService(
            ai_gateway=gateway,
            use_ai=True,
        )
        beats = rewriter.rewrite_episode(
            project,
            episode.episode_id,
            narration_style=tone,
            retelling_density=density,
        )
        return f"Imported review text for {len(beats)} beats"

    def _import_prompts(
        self,
        project: Project,
        result_data: dict[str, Any],
        episode_id: str | None,
        style_preset_id: str | None,
    ) -> str:
        episode = self._require_episode(project, episode_id)
        gateway = _SingleResponseGateway(result_data)
        builder = PromptBuilderService(
            ai_gateway=gateway,
            use_ai=True,
        )
        beats = builder.build_prompts_for_episode(
            project,
            episode.episode_id,
            style_preset_id=style_preset_id,
        )
        return f"Imported image prompts for {len(beats)} beats"

    # ── Helpers ───────────────────────────────────────────────────

    def _require_chapter(
        self, project: Project, chapter_id: str | None,
    ) -> SourceChapter:
        if not chapter_id:
            if not project.source_chapters:
                raise ValueError("No source chapters in project.")
            return project.source_chapters[0]
        for ch in project.source_chapters:
            if ch.chapter_id == chapter_id:
                return ch
        raise LookupError(f"SourceChapter not found: {chapter_id}")

    def _require_episode(self, project: Project, episode_id: str | None):
        if not episode_id:
            if not project.review_episodes:
                raise ValueError("No episodes in project.")
            return project.review_episodes[-1]
        return self.project_service.find_episode(project, episode_id)

    def _chapters_for_episode(
        self, project: Project, chapter_ids: list[str],
    ):
        chapters = []
        for cid in chapter_ids:
            for ch in project.source_chapters:
                if ch.chapter_id == cid:
                    chapters.append(ch)
                    break
        return chapters

    def _find_style_preset(self, project: Project, style_preset_id: str | None):
        if style_preset_id:
            for sp in project.style_presets:
                if sp.style_id == style_preset_id:
                    return sp
        elif project.style_presets:
            return project.style_presets[0]
        return None

    def _validate_step(self, step: str) -> None:
        if step not in SUPPORTED_STEPS:
            raise ValueError(
                f"Unsupported step '{step}'. "
                f"Supported: {', '.join(SUPPORTED_STEPS)}"
            )


class _SingleResponseGateway:
    """Gateway trả về kết quả cố định 1 lần — dùng để inject AI result."""

    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response

    def generate_text(
        self,
        prompt_name: str,
        input_data: dict[str, Any],
        system_message: str | None = None,
    ) -> str:
        return json.dumps(self._response, ensure_ascii=False)

    def generate_json(
        self,
        prompt_name: str,
        input_data: dict[str, Any],
        system_message: str | None = None,
    ) -> dict[str, Any]:
        return self._response
```

### Giải thích `_SingleResponseGateway`

Đây là trick quan trọng: Thay vì viết logic parse lại JSON response (trùng lặp với code các service đã có), ta tạo 1 gateway giả chỉ trả về đúng JSON mà user đã paste vào. Khi service gọi `gateway.generate_json()`, nó nhận được JSON của user → rồi service tự xử lý bằng code có sẵn (`_parsed_result_from_ai_response`, `_normalise_ai_plan`, v.v.).

---

### 4.2 CLI commands

Thêm vào `app/cli.py`:

#### Bước 1: Import ManualAIService

```python
# Thêm vào phần imports của cli.py
from app.services.manual_ai_service import ManualAIService, SUPPORTED_STEPS
```

#### Bước 2: Thêm subcommands vào `build_parser()`

Thêm trước dòng `return parser`:

```python
    # ── Manual AI workflow ───────────────────────────────────────
    export_prompt = subparsers.add_parser(
        "export-prompt",
        help="Export AI prompt for a pipeline step to paste into ChatGPT/Claude.",
    )
    export_prompt.add_argument("--project", required=True)
    export_prompt.add_argument(
        "--step", required=True, choices=SUPPORTED_STEPS,
        help="Pipeline step: parse-story, plan-episode, generate-beats, "
             "rewrite-review, build-prompts",
    )
    export_prompt.add_argument("--chapter-id", default=None)
    export_prompt.add_argument("--episode-id", default=None)
    export_prompt.add_argument("--tone", default=None)
    export_prompt.add_argument("--density", default=None)
    export_prompt.add_argument("--style-preset-id", default=None)
    export_prompt.add_argument("--output", required=True,
                               help="Output file (.json or .md)")
    export_prompt.set_defaults(handler=handle_export_prompt)

    import_result = subparsers.add_parser(
        "import-ai-result",
        help="Import AI JSON result from file and apply to project.",
    )
    import_result.add_argument("--project", required=True)
    import_result.add_argument(
        "--step", required=True, choices=SUPPORTED_STEPS,
    )
    import_result.add_argument("--result-file", required=True,
                               help="Path to JSON file with AI result.")
    import_result.add_argument("--chapter-id", default=None)
    import_result.add_argument("--episode-id", default=None)
    import_result.add_argument("--tone", default=None)
    import_result.add_argument("--density", default=None)
    import_result.add_argument("--style-preset-id", default=None)
    import_result.set_defaults(handler=handle_import_ai_result)
```

#### Bước 3: Thêm handler functions

```python
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
```

---

### 4.3 GUI — PySide6 UI

#### Thêm buttons vào `main_window.py`

##### Bước 1: Import ManualAIService

```python
# Thêm import
from app.services.manual_ai_service import ManualAIService, SUPPORTED_STEPS
```

##### Bước 2: Thêm buttons vào `_pipeline_group()`

Sửa method `_pipeline_group()` trong `MainWindow`:

```python
    def _pipeline_group(self) -> QGroupBox:
        group = QGroupBox("Pipeline")
        layout = QGridLayout(group)
        buttons = [
            ("Parse Story", self.parse_story),
            ("Generate Beats", self.generate_beats),
            ("Rewrite Review", self.rewrite_review),
            ("Build Prompts", self.build_prompts),
        ]
        for column, (label, callback) in enumerate(buttons):
            button = QPushButton(label)
            button.clicked.connect(callback)
            layout.addWidget(button, 0, column)
            layout.setColumnStretch(column, 1)

        # ── Manual AI buttons ──
        export_button = QPushButton("Export Prompt...")
        export_button.clicked.connect(self.export_ai_prompt)
        layout.addWidget(export_button, 1, 0, 1, 2)

        import_button = QPushButton("Import AI Result...")
        import_button.clicked.connect(self.import_ai_result)
        layout.addWidget(import_button, 1, 2, 1, 2)

        return group
```

##### Bước 3: Thêm methods vào `MainWindow`

```python
    def export_ai_prompt(self) -> None:
        """Export prompt cho user copy vào AI bên ngoài."""
        project = self.project_controller.require_project()
        settings = self.episode_panel.settings()

        # Chọn step
        step, ok = QInputDialog.getItem(
            self,
            "Export Prompt",
            "Chọn bước pipeline:",
            SUPPORTED_STEPS,
            0,
            False,
        )
        if not ok or not step:
            return

        # Chọn output file
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Prompt File",
            f"prompt_{step}.md",
            "Markdown (*.md);;JSON (*.json);;All Files (*)",
        )
        if not path:
            return

        def do_export():
            service = ManualAIService(self.project_controller.project_service)
            exported = service.export_prompt(
                project,
                step=step,
                chapter_id=self.selected_chapter_id,
                episode_id=self.selected_episode_id,
                tone=str(settings["tone"]),
                density=str(settings["density"]),
                style_preset_id=settings["style_preset_id"],
            )
            output_path = Path(path)
            if output_path.suffix == ".md":
                content = service.format_prompt_for_clipboard(exported)
            else:
                import json
                content = json.dumps(exported, ensure_ascii=False, indent=2)
            output_path.write_text(content, encoding="utf-8")
            return output_path

        result = self._run_ui_action(do_export, f"Exported prompt: {path}")
        if result:
            QMessageBox.information(
                self,
                "Export Prompt",
                f"Prompt đã lưu tại:\n{result}\n\n"
                "Mở file, copy nội dung vào ChatGPT/Claude.\n"
                "Lưu JSON result vào file .json rồi dùng 'Import AI Result'.",
            )

    def import_ai_result(self) -> None:
        """Import JSON result từ AI bên ngoài."""
        project = self.project_controller.require_project()
        settings = self.episode_panel.settings()

        # Chọn step
        step, ok = QInputDialog.getItem(
            self,
            "Import AI Result",
            "Bước pipeline tương ứng:",
            SUPPORTED_STEPS,
            0,
            False,
        )
        if not ok or not step:
            return

        # Chọn file JSON
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open AI Result File",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if not path:
            return

        def do_import():
            import json
            result_data = json.loads(Path(path).read_text(encoding="utf-8"))
            service = ManualAIService(self.project_controller.project_service)
            return service.import_result(
                project,
                step=step,
                result_data=result_data,
                chapter_id=self.selected_chapter_id,
                episode_id=self.selected_episode_id,
                tone=str(settings["tone"]),
                density=str(settings["density"]),
                style_preset_id=settings["style_preset_id"],
            )

        message = self._run_ui_action(do_import, "Imported AI result")
        if message:
            self.project_controller.save_project()
            self.refresh_all()
            QMessageBox.information(self, "Import Result", message)
```

---

## 5. Output schema cho từng bước

Khi user paste prompt vào ChatGPT, AI cần trả về JSON theo đúng schema. Dưới đây là schema cho mỗi step:

### Step 1: `parse-story`

```json
{
  "chapter_id": "ch_001",
  "detected_characters": [
    { "name": "Tên nhân vật", "role": "protagonist", "evidence": "..." }
  ],
  "detected_locations": [
    { "name": "Tên địa điểm", "mood": "mysterious" }
  ],
  "important_objects": ["object1"],
  "scene_candidates": [
    {
      "title": "Tên scene",
      "summary": "Mô tả scene",
      "importance": "high",
      "characters": ["Tên nhân vật"],
      "location": "Tên địa điểm",
      "mood": "tense"
    }
  ],
  "important_events": ["Sự kiện quan trọng"],
  "continuity_notes": ["Ghi chú liên tục"]
}
```

### Step 2: `plan-episode`

```json
{
  "episode": {
    "episode_title": "Tên episode",
    "episode_summary": "Tóm tắt episode",
    "source_chapter_ids": ["ch_001"],
    "tone": "mysterious",
    "density": "full",
    "hook": "Câu hook mở đầu"
  },
  "scenes": [
    {
      "scene_id": "sc_001",
      "title": "Tên scene",
      "summary": "Mô tả scene",
      "mood": "tense",
      "characters": ["character_id"],
      "location": "location_id",
      "target_beats": 4,
      "importance": "high"
    }
  ],
  "cliffhanger": "Câu cliffhanger kết episode"
}
```

### Step 3: `generate-beats`

```json
{
  "beats": [
    {
      "beat_id": "beat_sc_001_001",
      "scene_id": "sc_001",
      "order_index": 1,
      "story_function": "discovery",
      "characters": ["character_id"],
      "location": "location_id",
      "action": "Hành động cụ thể",
      "emotion": "curious",
      "shot_type": "medium shot",
      "visual_description": "Mô tả hình ảnh chi tiết",
      "continuity_tags": ["tag1", "tag2"]
    }
  ]
}
```

### Step 4: `rewrite-review`

```json
{
  "rewritten_beats": [
    {
      "beat_id": "beat_sc_001_001",
      "review_text": "Nội dung review narration bằng tiếng Việt..."
    }
  ]
}
```

### Step 5: `build-prompts`

```json
{
  "prompts": [
    {
      "beat_id": "beat_sc_001_001",
      "image_prompt": "English image prompt for AI image generation...",
      "negative_prompt": "blurry, low quality, text, watermark"
    }
  ]
}
```

---

## 6. Ví dụ sử dụng end-to-end

### Qua CLI

```bash
# 1. Tạo project + thêm chapter (như bình thường)
python -m app.cli create-project --title "Test" --output project.json
python -m app.cli add-chapter --project project.json \
    --title "Chapter 1" --chapter-number 1 --text-file chapter1.txt

# 2. Export prompt cho step parse-story
python -m app.cli export-prompt \
    --project project.json \
    --step parse-story \
    --chapter-id ch_001 \
    --output prompt_parse.md

# 3. User mở prompt_parse.md → copy vào ChatGPT → lấy JSON result
#    Lưu result vào file parse_result.json

# 4. Import result
python -m app.cli import-ai-result \
    --project project.json \
    --step parse-story \
    --chapter-id ch_001 \
    --result-file parse_result.json

# 5. Tiếp tục với step tiếp theo...
python -m app.cli export-prompt \
    --project project.json \
    --step plan-episode \
    --chapter-id ch_001 \
    --output prompt_plan.md

# ... lặp lại cho từng step
```

### Qua GUI

1. Mở project → chọn chapter/episode
2. Click **"Export Prompt..."** → chọn step → save file `.md`
3. Mở file `.md` → copy toàn bộ nội dung → paste vào ChatGPT/Claude
4. Copy JSON result từ AI → lưu vào file `.json`
5. Click **"Import AI Result..."** → chọn step → chọn file `.json`
6. App tự áp dụng result → refresh UI
7. Lặp lại cho step tiếp theo

---

## 7. Test plan

Tạo file `tests/test_manual_ai_service.py`:

```python
"""Tests for ManualAIService."""

from __future__ import annotations

import json
import pytest

from app.services.manual_ai_service import ManualAIService, SUPPORTED_STEPS
from app.services.project_service import ProjectService


@pytest.fixture
def project_with_chapter():
    """Tạo project có sẵn 1 chapter để test."""
    service = ProjectService()
    project = service.create_project("Test Project")
    service.add_source_chapter(
        project,
        title="Chapter 1",
        chapter_number=1,
        raw_text="Nhân vật chính bước vào căn nhà hoang. "
                 "Anh ta phát hiện một manh mối kỳ lạ trên sàn.",
    )
    return project, service


class TestExportPrompt:
    def test_export_all_steps_have_template_and_input(self, project_with_chapter):
        project, ps = project_with_chapter
        service = ManualAIService(ps)

        for step in SUPPORTED_STEPS:
            kwargs = {"step": step}
            if step in ("parse-story", "plan-episode"):
                kwargs["chapter_id"] = project.source_chapters[0].chapter_id
            else:
                # Các step sau cần episode — skip nếu chưa có
                continue

            exported = service.export_prompt(project, **kwargs)
            assert "prompt_template" in exported
            assert "input_data" in exported
            assert exported["step"] == step
            assert len(exported["prompt_template"]) > 0

    def test_format_for_clipboard(self, project_with_chapter):
        project, ps = project_with_chapter
        service = ManualAIService(ps)
        exported = service.export_prompt(
            project,
            step="parse-story",
            chapter_id=project.source_chapters[0].chapter_id,
        )
        text = service.format_prompt_for_clipboard(exported)
        assert "## Runtime input" in text
        assert "```json" in text

    def test_unsupported_step_raises(self, project_with_chapter):
        project, ps = project_with_chapter
        service = ManualAIService(ps)
        with pytest.raises(ValueError, match="Unsupported step"):
            service.export_prompt(project, step="invalid-step")


class TestImportResult:
    def test_import_parse_result(self, project_with_chapter):
        project, ps = project_with_chapter
        service = ManualAIService(ps)
        result = {
            "chapter_id": project.source_chapters[0].chapter_id,
            "detected_characters": [
                {"name": "Nhân vật chính", "role": "protagonist", "evidence": "test"}
            ],
            "detected_locations": [
                {"name": "Căn nhà hoang", "mood": "mysterious"}
            ],
            "scene_candidates": [
                {
                    "title": "Scene test",
                    "summary": "Test summary",
                    "importance": "high",
                    "characters": ["Nhân vật chính"],
                    "location": "Căn nhà hoang",
                    "mood": "mysterious",
                }
            ],
            "important_events": ["Test event"],
        }
        message = service.import_result(
            project,
            step="parse-story",
            result_data=result,
            chapter_id=project.source_chapters[0].chapter_id,
        )
        assert "Imported" in message
        assert "1 scenes" in message

    def test_import_plan_result(self, project_with_chapter):
        project, ps = project_with_chapter
        service = ManualAIService(ps)
        chapter_id = project.source_chapters[0].chapter_id
        result = {
            "episode": {
                "episode_title": "Test Episode",
                "episode_summary": "Test summary",
                "source_chapter_ids": [chapter_id],
                "tone": "mysterious",
                "density": "full",
                "hook": "Test hook",
            },
            "scenes": [
                {
                    "scene_id": "sc_test_001",
                    "title": "Test scene",
                    "summary": "Scene summary",
                    "mood": "tense",
                    "characters": ["protagonist"],
                    "location": "location",
                    "target_beats": 3,
                    "importance": "high",
                }
            ],
            "cliffhanger": "Test cliffhanger",
        }
        message = service.import_result(
            project,
            step="plan-episode",
            result_data=result,
            chapter_id=chapter_id,
        )
        assert "Imported episode" in message
        assert len(project.review_episodes) > 0
```

### Chạy tests

```bash
python -m pytest tests/test_manual_ai_service.py -v
```

---

## Lưu ý quan trọng

1. **Không cần sửa các service gốc** — ManualAIService chỉ gọi lại methods có sẵn.

2. **`_SingleResponseGateway`** là chìa khóa — nó giả làm AI gateway, trả về đúng JSON user đã paste. Các service xử lý result giống hệt như khi dùng AI thật.

3. **Export `.md` vs `.json`**:
   - `.md` = sẵn sàng copy-paste (prompt + input gộp thành 1 text)
   - `.json` = chứa metadata (step name, prompt riêng, input riêng)

4. **Thứ tự pipeline phải tuân thủ**:
   ```
   parse-story → plan-episode → generate-beats → rewrite-review → build-prompts
   ```
   Không thể skip step (ví dụ: không thể generate-beats khi chưa có episode).

5. **Mỗi step cần context khác nhau**:
   - `parse-story` + `plan-episode`: cần `--chapter-id`
   - `generate-beats` + `rewrite-review` + `build-prompts`: cần `--episode-id`
