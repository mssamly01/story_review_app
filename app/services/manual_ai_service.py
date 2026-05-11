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
    "generate-unified-package",
]

_STEP_TO_PROMPT_NAME = {
    "parse-story": "story_parser",
    "plan-episode": "episode_planner",
    "generate-beats": "beat_generator",
    "rewrite-review": "review_rewriter",
    "build-prompts": "image_prompt_builder",
    "generate-unified-package": "beat_package_generator",
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
                "Copy toàn bộ nội dung bên dưới vào ChatGPT/Claude/Gemini.\\n"
                "AI sẽ trả về JSON theo output schema.\\n"
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
        return f"{template.rstrip()}\\n\\n## Runtime input\\n```json\\n{payload}\\n```"

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
        if step == "generate-unified-package":
            return self._import_unified_package(
                project, result_data, episode_id
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
        if step == "generate-unified-package":
            return self._input_unified_package(project, episode_id)
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
        return {
            "episode": episode.to_dict(),
            "source_chapters": [
                {
                    "chapter_id": ch.chapter_id,
                    "title": ch.title,
                    "raw_text": ch.raw_text,
                }
                for ch in source_chapters
            ],
            "scenes": [scene.to_dict() for scene in episode.scenes],
            "retelling_density": density or episode.density,
            "character_bible": [c.to_dict() for c in project.characters],
            "location_bible": [loc.to_dict() for loc in project.locations],
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
        
        all_beats = []
        for scene in episode.scenes:
            for beat in scene.ordered_beats():
                # Include minimal scene info with beat
                b_dict = beat.to_dict()
                b_dict["scene_title"] = scene.title
                b_dict["scene_summary"] = scene.summary
                all_beats.append(b_dict)

        return {
            "episode": episode.to_dict(),
            "source_chapters": [ch.to_dict() for ch in source_chapters],
            "beats": all_beats,
            "narration_style": tone or episode.tone,
            "retelling_density": density or episode.density,
        }

    def _input_prompts(
        self,
        project: Project,
        episode_id: str | None,
        style_preset_id: str | None,
    ) -> dict[str, Any]:
        episode = self._require_episode(project, episode_id)
        style_preset = self._find_style_preset(project, style_preset_id)

        all_beats = []
        for scene in episode.scenes:
            for beat in scene.ordered_beats():
                b_dict = beat.to_dict()
                b_dict["scene_title"] = scene.title
                all_beats.append(b_dict)

        return {
            "episode": episode.to_dict(),
            "beats": all_beats,
            "character_bible": [c.to_dict() for c in project.characters],
            "location_bible": [loc.to_dict() for loc in project.locations],
            "style_preset": (style_preset.to_dict() if style_preset else {}),
        }

    def _input_unified_package(
        self, project: Project, episode_id: str | None
    ) -> dict[str, Any]:
        episode = self._require_episode(project, episode_id)
        source_chapters = self._chapters_for_episode(
            project, episode.source_chapter_ids
        )
        style_preset = self._find_style_preset(project, project.default_art_style)

        return {
            "project_context": {
                "title": project.title,
                "genre": project.genre,
                "language": project.language,
                "narration_style": project.default_narration_style,
                "retelling_density": project.retelling_density,
                "art_style": project.default_art_style,
            },
            "episode": {
                "episode_id": episode.episode_id,
                "episode_title": episode.title,
                "episode_summary": episode.summary,
                "tone": episode.tone,
                "density": episode.density,
            },
            "scenes": [scene.to_dict() for scene in episode.scenes],
            "source_chapters": [
                {
                    "chapter_id": ch.chapter_id,
                    "title": ch.title,
                    "raw_text": ch.raw_text,
                }
                for ch in source_chapters
            ],
            "character_bible": [c.to_dict() for c in project.characters],
            "location_bible": [loc.to_dict() for loc in project.locations],
            "style_preset": (style_preset.to_dict() if style_preset else {}),
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

        # Cập nhật Bible thầm lặng
        new_chars = 0
        existing_char_names = {c.name.lower() for c in project.characters}
        for det_char in parsed.detected_characters:
            if det_char.name.lower() not in existing_char_names:
                self.project_service.add_character(
                    project,
                    name=det_char.name,
                    role=det_char.role
                )
                existing_char_names.add(det_char.name.lower())
                new_chars += 1

        new_locs = 0
        existing_loc_names = {l.name.lower() for l in project.locations}
        for det_loc in parsed.detected_locations:
            if det_loc.name.lower() not in existing_loc_names:
                self.project_service.add_location(
                    project,
                    name=det_loc.name,
                    mood=det_loc.mood
                )
                existing_loc_names.add(det_loc.name.lower())
                new_locs += 1

        return (
            f"Imported parse result: {parsed.chapter_id} — "
            f"{len(parsed.scene_candidates)} scenes, "
            f"{new_chars} characters added, {new_locs} locations added"
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

    def _import_unified_package(
        self,
        project: Project,
        result_data: dict[str, Any],
        episode_id: str | None,
    ) -> str:
        episode = self._require_episode(project, episode_id)
        
        # We can reuse BeatPackageGeneratorService logic if we wrap the result
        from app.services.beat_package_generator_service import BeatPackageGeneratorService
        gateway = _SingleResponseGateway(result_data)
        service = BeatPackageGeneratorService(
            project_service=self.project_service,
            ai_gateway=gateway
        )
        
        total_beats = 0
        # If the JSON contains a list of scenes, we might need to handle it differently
        # but BeatPackageGeneratorService expects {"beats": [...]} for a single scene call.
        # Let's check the schema the user requested.
        
        if "scenes" in result_data:
            for scene_data in result_data["scenes"]:
                scene_id = scene_data.get("scene_id")
                if not scene_id: continue
                
                # Mock a gateway that returns the beats for THIS specific scene
                scene_gateway = _SingleResponseGateway({"beats": scene_data.get("beats", [])})
                scene_service = BeatPackageGeneratorService(
                    project_service=self.project_service,
                    ai_gateway=scene_gateway
                )
                
                # Use generate_for_scene in AI mode (it will call our mock gateway)
                beats = scene_service.generate_for_scene(
                    project, episode.episode_id, scene_id, use_ai=True
                )
                total_beats += len(beats)
        elif "beats" in result_data:
            # Fallback if AI returned beats directly without scene nesting
            # (or if we are in a single-scene mode)
            # This is less ideal but good for robustness
            pass

        return f"Imported unified package: {total_beats} beats applied across scenes."

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
