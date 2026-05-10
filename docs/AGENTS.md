# AGENTS.md — Hướng dẫn AI Coding Agent

## 1. Vai trò của AI agent

AI coding agent phải hỗ trợ xây dựng ứng dụng theo hướng:

> Comic-style review text and image prompt generator for long-form stories.

Không được biến project thành:

- Video editor
- Timeline editor
- Full comic drawing tool
- Image generation platform hoàn chỉnh
- Social publishing tool

App chỉ tập trung vào:

- Quản lý truyện dài tập
- Chia episode/scene/beat
- Viết lại thành review text
- Tạo prompt ảnh nhất quán
- Xuất dữ liệu

---

## 2. Nguyên tắc làm việc cho AI agent

### Rule 1: Domain-first

Mọi tính năng phải bắt đầu từ domain model trước UI.

Thứ tự ưu tiên:

```text
domain → services → controllers → UI → export
```

### Rule 2: Beat là trung tâm

Nếu không chắc thiết kế tính năng đặt ở đâu, hãy hỏi:

> Tính năng này có phục vụ việc tạo, sửa, kiểm tra hoặc xuất Beat không?

Nếu có, nó thuộc core app.

### Rule 3: Không hard-code prompt lung tung

Prompt phải được tạo bởi `PromptBuilderService`, dựa trên:

- StylePreset
- Character.visual_prompt_base
- Location.visual_prompt_base
- Beat.action
- Beat.emotion
- Beat.shot_type

### Rule 4: Không để UI gọi AI trực tiếp

UI không được gọi model/AI API trực tiếp.

Đúng:

```text
UI → Controller → Service → AI Gateway
```

Sai:

```text
UI → AI API
```

### Rule 5: Project JSON phải đọc được bởi con người

Project file cần dễ đọc, dễ debug, không binary hóa dữ liệu.

### Rule 6: Không phá dữ liệu gốc

Source text phải được giữ nguyên. Mọi nội dung viết lại phải lưu ở layer riêng.

### Rule 7: Không copy nguyên văn dài

`ReviewRewriterService` phải ưu tiên diễn giải lại bằng lời mới, trừ khi người dùng cố ý yêu cầu trích dẫn ngắn.

---

## 3. Cấu trúc thư mục đề xuất

```text
app/
  main.py
  bootstrap.py

  domain/
    project.py
    source_chapter.py
    episode.py
    scene.py
    beat.py
    character.py
    location.py
    style_preset.py
    continuity.py

  services/
    project_service.py
    source_import_service.py
    story_parser_service.py
    episode_planner_service.py
    beat_generator_service.py
    review_rewriter_service.py
    prompt_builder_service.py
    continuity_checker_service.py
    export_service.py

  controllers/
    project_controller.py
    source_controller.py
    episode_controller.py
    beat_controller.py
    bible_controller.py
    generation_controller.py
    export_controller.py

  infrastructure/
    ai_gateway.py
    file_storage.py
    id_generator.py

  ui/
    main_window.py
    project_panel.py
    source_editor.py
    episode_outline_view.py
    beat_editor.py
    bible_panel.py
    prompt_preview.py
    export_panel.py

  prompts/
    story_parser_prompt.md
    episode_planner_prompt.md
    beat_generator_prompt.md
    review_rewriter_prompt.md
    image_prompt_builder_prompt.md
    continuity_checker_prompt.md

  tests/
    test_project_service.py
    test_episode_planner_service.py
    test_beat_generator_service.py
    test_review_rewriter_service.py
    test_prompt_builder_service.py
    test_export_service.py
```

---

## 4. Coding standards

### Python style

- Use dataclasses or Pydantic models for domain entities
- Use type hints
- Keep services pure where possible
- Avoid business logic in UI
- Avoid global state
- Prefer small functions
- Write tests for core services

### Naming

Use explicit names:

```python
ReviewEpisode
NarrativeBeat
PromptBuilderService
CharacterBible
LocationBible
```

Avoid vague names:

```python
Data
Item
Thing
Processor
Manager
```

---

## 5. AI prompt files

The app should keep reusable prompt templates in `app/prompts/`.

Each prompt file should define:

- Role
- Task
- Input schema
- Output schema
- Rules
- Example output

Prompt files should not be scattered inside UI code.

---

## 6. Required services

### ProjectService

Responsibilities:

- Create project
- Save project
- Load project
- Validate project structure

Should not:

- Generate AI text
- Build prompts
- Know about UI

---

### StoryParserService

Responsibilities:

- Parse source chapter
- Extract characters
- Extract locations
- Identify scenes
- Identify important events

Input:

```python
SourceChapter
```

Output:

```python
ParsedChapterResult
```

---

### EpisodePlannerService

Responsibilities:

- Create ReviewEpisode from one or more source chapters
- Decide scene structure
- Estimate beat count
- Select cliffhanger point

---

### BeatGeneratorService

Responsibilities:

- Convert scenes into narrative beats
- Assign story function
- Assign character/location/emotion/action
- Suggest shot type

---

### ReviewRewriterService

Responsibilities:

- Rewrite each beat into narration/review text
- Respect tone and density
- Avoid excessive copying
- Maintain continuity

---

### PromptBuilderService

Responsibilities:

- Build image prompt from beat + bible + style
- Build negative prompt
- Keep prompt structure consistent

---

### ContinuityCheckerService

Responsibilities:

- Check character consistency
- Check location consistency
- Check outfit continuity
- Check object continuity
- Check emotional continuity

---

### ExportService

Responsibilities:

- Export Markdown
- Export JSON
- Export CSV
- Export TXT

---

## 7. Output schema rule for AI calls

All AI generation services should request JSON output when possible.

Bad:

```text
Write me some scenes.
```

Good:

```json
{
  "scenes": [
    {
      "scene_id": "sc_001",
      "title": "...",
      "summary": "...",
      "characters": [],
      "location": "...",
      "mood": "...",
      "important_events": []
    }
  ]
}
```

---

## 8. Testing requirements

Minimum tests:

- Project can save/load without losing data
- Source chapter can be added to project
- Episode can reference source chapters
- Scene can contain ordered beats
- Beat can store review text and prompt
- PromptBuilder uses character/location/style data
- ExportService outputs valid Markdown/JSON/CSV

---

## 9. Definition of Done

A feature is done only when:

- Domain model exists
- Service logic exists
- Controller method exists if UI needs it
- UI displays or edits it if required
- Data is saved/loaded correctly
- Basic test exists
- Export does not break

---

## 10. Implementation guardrails

AI agent must not:

- Add video editing features
- Add audio timeline features
- Add complex image editor features
- Store generated content only in UI state
- Mix source text and rewritten review text in the same field
- Generate prompts without checking character/location/style context

AI agent should always preserve this pipeline:

```text
SourceChapter
→ Parsed scenes
→ ReviewEpisode
→ Scene
→ Beat
→ Review text
→ Image prompt
→ Export
```
