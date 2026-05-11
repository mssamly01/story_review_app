# Story Review Studio

> Comic-style review production system: import truyện dài tập, chia thành
> Episode → Scene → Beat, viết lại thành review narration tiếng Việt, sinh
> prompt ảnh nhất quán cho từng beat dựa trên Character Bible + Location
> Bible + Style Preset, rồi export Markdown / JSON / CSV / TXT.

App tập trung vào **pre-image production layer**: sinh script review +
image prompt chuẩn để người dùng tự render ảnh ở Midjourney / Stable
Diffusion / ComfyUI / DALL·E. App không phải video editor, không phải
manga drawing tool, không phải image generation platform hoàn chỉnh.

## Pipeline

```text
SourceChapter
  → Parse  (StoryParserService — tách scene, nhận diện nhân vật/địa điểm)
  → Build Bible  (Character / Location / StylePreset)
  → Plan Episode  (EpisodePlannerService — chọn chapter, dồn thành episode)
  → Split into Scenes
  → Generate Beats  (BeatGeneratorService — atomic narrative moment)
  → Rewrite Review Text  (ReviewRewriterService — voice-over narration)
  → Build Image Prompts  (PromptBuilderService — deterministic, không AI)
  → Check Continuity  (ContinuityCheckerService)
  → Export  (Markdown / JSON / CSV / TXT)
```

## Tech stack

- **Python 3.11+**
- **PySide6** — desktop UI multi-tab (`Dự án | Nguồn | Kế hoạch tập | Beat Studio | Bible/Style | Chất lượng | Xuất bản`)
- **argparse CLI** — `python -m app.cli` với 30+ subcommand
- **AI Gateway** — abstract interface, có 2 implementation:
  - `MockAIGateway` (default, không cần API key — dùng cho test/dev)
  - `OpenAIAIGateway` (gọi GPT-4.1-mini Responses API)
  - **Manual AI mode**: copy prompt → ChatGPT/Claude ngoài → paste JSON result về app
- **JSON persistence** — human-readable, không binary

## Quick start

```bash
# 1. Clone
git clone https://github.com/mssamly01/story_review_app
cd story_review_app

# 2. Cài
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. (Tuỳ chọn) Cài AI dependency để gọi provider thật
pip install -r requirements-ai.txt

# Chọn provider qua env (default = openai). Đặt cred tương ứng:
export OPENAI_API_KEY="sk-..."              # openai
# export ANTHROPIC_API_KEY="sk-ant-..."     # anthropic
# export GEMINI_API_KEY="..."               # gemini (hoặc GOOGLE_API_KEY)
# export OLLAMA_HOST="http://localhost:11434"  # ollama (local)

# Hoặc chọn provider qua flag/env runtime:
#   AI_PROVIDER=anthropic python -m app.cli ... --real-ai
#   python -m app.cli ... --real-ai --provider gemini

# 3b. (Cho người đóng góp code) Cài dev tooling
pip install -r requirements-dev.txt
pre-commit install

# 4. Chạy desktop app
python -m app

# 5. Hoặc dùng CLI
python -m app.cli create-project --title "Căn nhà cũ" --output my_project.json
python -m app.cli add-chapter --project my_project.json \
  --title "Chương 1" --chapter-number 1 --text-file chapter1.txt
python -m app.cli run-pipeline --project my_project.json --mock-ai

# 6. Export
python -m app.cli export --project my_project.json \
  --episode ep_001 --format markdown --output ep001.md
```

## Dev workflow

```bash
# Chạy test (offline, không cần OPENAI_API_KEY)
python -m pytest tests/ -q

# Lint + format check (cũng chạy trong CI)
ruff check .
black --check .

# Format tự động
ruff check --fix .
black .

# Chạy mọi pre-commit hook trên toàn repo
pre-commit run --all-files
```

CI ở [`.github/workflows/ci.yml`](.github/workflows/ci.yml) chạy `pytest`,
`ruff check`, `black --check` trên Python 3.11 và 3.12 cho mọi PR.

## Tài liệu

- [`docs/AGENTS.md`](docs/AGENTS.md) — guard rail cho AI coding agent (đọc trước khi sửa code)
- [`docs/DESIGN.md`](docs/DESIGN.md) — thiết kế domain model + 9 màn hình UI
- [`docs/PLAN.md`](docs/PLAN.md) — 7 nguyên tắc sản phẩm + MVP roadmap
- [`docs/SKILL.md`](docs/SKILL.md) — chi tiết prompt engineering cho từng bước AI
- [`examples/`](examples/) — sample project JSON sẵn sàng load (xem `examples/README.md`)

## Trạng thái

- **Tests:** 302 test, 48 subtest — passing
- **Stage:** Pre-production, hoàn thiện kiến trúc 7-bước, đang polish

## License

Chưa quyết định (TBD).
