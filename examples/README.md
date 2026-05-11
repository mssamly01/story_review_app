# Examples

Small, ready-to-load sample projects for kicking the tyres on the CLI and the
desktop app without typing anything yourself.

## `can_nha_cu.json`

A minimal dark-fantasy review project (`Căn nhà cũ` — "The old house"), in
Vietnamese, containing:

- 1 source chapter (~60 words).
- 1 character (`Lâm Vũ`) with a `visual_prompt_base` ready for image rendering.
- 1 location (`Căn nhà cũ`) with a matching visual prompt.
- 1 style preset (`Dark Fantasy Webtoon`).
- 1 review episode → 1 scene → 3 beats, each with `review_text`,
  `image_prompt`, and `negative_prompt` already filled in.

### Try it

```bash
# 1. Inspect — just open the JSON, it is plain UTF-8.

# 2. Load via the CLI and rebuild the deterministic image prompts:
python -m app.cli build-prompts \
    --project examples/can_nha_cu.json \
    --episode-id ep_001

# 3. Run a full pipeline pass (parse → plan → beats → rewrite → prompts → export)
#    against the mock AI gateway, no API key required:
python -m app.cli run-pipeline \
    --project examples/can_nha_cu.json \
    --chapter-id ch_001 \
    --episode-title "Trở về căn nhà cũ" \
    --output /tmp/can_nha_cu_pipeline.md \
    --mock-ai

# 4. Or load it in the desktop UI:
python -m app
# → File / Mở dự án → examples/can_nha_cu.json
```

### How it was generated

Created with `app.services.project_service.ProjectService` (no AI, just
deterministic `add_*` calls). The same approach works for any sample — see the
`add_source_chapter`, `add_character`, `add_location`, `add_review_episode`,
`add_scene`, `add_beat` methods on `ProjectService`.

If you tweak the example, please:

- Keep the file small (<10 KB) so the test corpus stays cheap.
- Re-save via `ProjectService.save_project` so the field ordering and encoding
  stay consistent with the rest of the codebase.
