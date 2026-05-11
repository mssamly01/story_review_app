"""Load reusable generation prompt templates."""

from __future__ import annotations

from pathlib import Path


class PromptTemplateLoader:
    PROMPT_FILES = {
        "story_parser": "story_parser_prompt.md",
        "episode_planner": "episode_planner_prompt.md",
        "beat_generator": "beat_generator_prompt.md",
        "review_rewriter": "review_rewriter_prompt.md",
        "image_prompt_builder": "image_prompt_builder_prompt.md",
        "continuity_checker": "continuity_checker_prompt.md",
        "beat_package_generator": "beat_package_generator_prompt.md",
    }

    def __init__(self, prompts_dir: str | Path | None = None) -> None:
        self.prompts_dir = (
            Path(prompts_dir)
            if prompts_dir is not None
            else Path(__file__).resolve().parents[1] / "prompts"
        )

    def load(self, prompt_name: str) -> str:
        path = self._template_path(prompt_name)
        if not path.exists():
            raise FileNotFoundError(
                f"Prompt template file is missing for '{prompt_name}': {path}"
            )
        return path.read_text(encoding="utf-8")

    def exists(self, prompt_name: str) -> bool:
        try:
            return self._template_path(prompt_name).exists()
        except ValueError:
            return False

    def _template_path(self, prompt_name: str) -> Path:
        filename = self.PROMPT_FILES.get(prompt_name)
        if filename is None:
            supported = ", ".join(sorted(self.PROMPT_FILES))
            raise ValueError(
                f"Unknown prompt template '{prompt_name}'. "
                f"Supported prompt templates: {supported}."
            )
        return self.prompts_dir / filename
