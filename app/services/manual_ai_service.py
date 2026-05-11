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
                project,
                result_data,
                chapter_id,
                tone,
                density,
            )
        if step == "generate-beats":
            return self._import_beats(project, result_data, episode_id, density, chapter_id)
        if step == "rewrite-review":
            return self._import_rewrite(
                project,
                result_data,
                episode_id,
                chapter_id,
                tone,
                density,
            )
        if step == "build-prompts":
            return self._import_prompts(
                project,
                result_data,
                episode_id,
                chapter_id,
                style_preset_id,
            )
        if step == "generate-unified-package":
            return self._import_unified_package(project, result_data, episode_id, chapter_id)
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
        self,
        project: Project,
        chapter_id: str | None,
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
            project,
            episode.source_chapter_ids,
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
            "style_preset": (self._find_style_preset(project, project.default_art_style).to_dict() if self._find_style_preset(project, project.default_art_style) else {}),
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
            project,
            episode.source_chapter_ids,
        )
        scenes_input = []
        for scene in episode.scenes:
            scenes_input.append(
                {
                    "scene": scene.to_dict(),
                    "beats": [beat.to_dict() for beat in scene.ordered_beats()],
                    "narration_style": tone or episode.tone,
                    "retelling_density": density or episode.density,
                }
            )
        return {
            "episode_id": episode.episode_id,
            "episode_title": episode.title,
            "source_chapter_context": [
                {
                    "chapter_id": ch.chapter_id,
                    "title": ch.title,
                    "raw_text": ch.raw_text,
                }
                for ch in source_chapters
            ],
            "scenes": scenes_input,
        }

    def _input_prompts(
        self,
        project: Project,
        episode_id: str | None,
        style_preset_id: str | None,
    ) -> dict[str, Any]:
        episode = self._require_episode(project, episode_id)
        style_preset = self._find_style_preset(project, style_preset_id)
        scenes_input = []
        for scene in episode.scenes:
            scenes_input.append(
                {
                    "scene": scene.to_dict(),
                    "beats": [beat.to_dict() for beat in scene.ordered_beats()],
                }
            )
        return {
            "episode_id": episode.episode_id,
            "episode_title": episode.title,
            "character_bible": [c.to_dict() for c in project.characters],
            "location_bible": [loc.to_dict() for loc in project.locations],
            "style_preset": style_preset.to_dict() if style_preset else {},
            "scenes": scenes_input,
        }

    def _input_unified_package(self, project: Project, episode_id: str | None) -> dict[str, Any]:
        episode = self._require_episode(project, episode_id)
        source_chapters = self._chapters_for_episode(project, episode.source_chapter_ids)
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
                self.project_service.add_character(project, name=det_char.name, role=det_char.role)
                existing_char_names.add(det_char.name.lower())
                new_chars += 1

        new_locs = 0
        existing_loc_names = {l.name.lower() for l in project.locations}
        for det_loc in parsed.detected_locations:
            if det_loc.name.lower() not in existing_loc_names:
                self.project_service.add_location(project, name=det_loc.name, mood=det_loc.mood)
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
        return f"Imported episode: {episode.episode_id} " f"({len(episode.scenes)} scenes)"

    def _import_beats(
        self,
        project: Project,
        result_data: dict[str, Any],
        episode_id: str | None,
        density: str | None,
        chapter_id: str | None = None,
    ) -> str:
        episode = self._require_episode(project, episode_id)
        
        # 1. Group beats by their own scene_id if available
        grouped = self._group_beats_by_scene(result_data, "beats")
        
        # 2. If we only have "unknown" beats and user has a selected scene, map them there
        if len(grouped) == 1 and "unknown" in grouped and chapter_id:
            grouped[chapter_id] = grouped.pop("unknown")
        
        # 3. If still unknown and no selection, error out
        if "unknown" in grouped:
            raise ValueError("Không thể xác định scene_id cho các nhịp truyện. Vui lòng cung cấp scene_id hoặc chọn một phân cảnh trước khi nhập.")

        total_beats = 0
        affected_scenes = 0

        for sid, beats in grouped.items():
            if not beats: continue
            
            # Ensure scene exists or create minimal one
            try:
                self.project_service.find_scene(project, episode.episode_id, sid)
            except LookupError:
                self.project_service.add_scene(
                    project,
                    episode_id=episode.episode_id,
                    title=f"Scene {sid}",
                    scene_id=sid
                )
            
            gateway = _SingleResponseGateway({"beats": beats})
            generator = BeatGeneratorService(self.project_service, ai_gateway=gateway, use_ai=True)
            b = generator.generate_beats_for_scene(project, episode.episode_id, sid, density)
            total_beats += len(b)
            affected_scenes += 1
            
        return f"Đã nhập {total_beats} nhịp truyện cho {affected_scenes} phân cảnh."

    def _import_rewrite(
        self,
        project: Project,
        result_data: dict[str, Any],
        episode_id: str | None,
        chapter_id: str | None,
        tone: str | None,
        density: str | None,
    ) -> str:
        episode = self._require_episode(project, episode_id)
        grouped = self._group_beats_by_scene(result_data, "rewritten_beats")
        total_beats = 0
        
        if chapter_id:
            beats = grouped.get(chapter_id, []) or grouped.get("unknown", [])
            if beats:
                gateway = _SingleResponseGateway({"rewritten_beats": beats})
                rewriter = ReviewRewriterService(ai_gateway=gateway, use_ai=True)
                b = rewriter.rewrite_scene(project, chapter_id, narration_style=tone, retelling_density=density)
                total_beats = len(b)
            return f"Đã cập nhật review cho {total_beats} nhịp của phân cảnh đang chọn."
        else:
            for sid, beats in grouped.items():
                if sid == "unknown": continue
                gateway = _SingleResponseGateway({"rewritten_beats": beats})
                rewriter = ReviewRewriterService(ai_gateway=gateway, use_ai=True)
                try:
                    b = rewriter.rewrite_scene(project, sid, narration_style=tone, retelling_density=density)
                    total_beats += len(b)
                except LookupError: continue
            return f"Đã cập nhật review cho {total_beats} nhịp trên toàn tập."

    def _import_prompts(
        self,
        project: Project,
        result_data: dict[str, Any],
        episode_id: str | None,
        chapter_id: str | None,
        style_preset_id: str | None,
    ) -> str:
        episode = self._require_episode(project, episode_id)
        
        # 1. Collect all beats from input data
        raw_beats: list[dict] = []
        if "scenes" in result_data and isinstance(result_data["scenes"], list):
            for scene_data in result_data["scenes"]:
                s_beats = scene_data.get("beats", [])
                for b in s_beats:
                    if isinstance(b, dict):
                        # Inherit scene_id if missing
                        if "scene_id" not in b and "scene_id" in scene_data:
                            b["scene_id"] = scene_data["scene_id"]
                        raw_beats.append(b)
        
        if not raw_beats:
            raw_beats = result_data.get("prompts", []) or result_data.get("beats", [])

        if not isinstance(raw_beats, list):
            return "Không tìm thấy dữ liệu nhịp truyện hợp lệ."

        # 2. Map beat_id -> data
        beat_map: dict[str, dict] = {}
        for b in raw_beats:
            if not isinstance(b, dict): continue
            bid = b.get("beat_id")
            if bid:
                beat_map[bid] = b

        total_updated = 0
        affected_scenes = set()
        total_input = len(beat_map)

        # 3. Update existing beats in the episode
        for scene in episode.scenes:
            for beat in scene.beats:
                if beat.beat_id in beat_map:
                    data = beat_map[beat.beat_id]
                    
                    # Update fields
                    if "image_prompt" in data:
                        beat.image_prompt = data["image_prompt"]
                    if "negative_prompt" in data:
                        beat.negative_prompt = data["negative_prompt"]
                    if "visual_description" in data:
                        beat.visual_description = data["visual_description"]
                    if "continuity_tags" in data and isinstance(data["continuity_tags"], list):
                        beat.continuity_tags = data["continuity_tags"]
                    
                    total_updated += 1
                    affected_scenes.add(scene.scene_id)

        skipped = total_input - total_updated
        msg = f"Đã cập nhật prompt cho {total_updated} nhịp trong {len(affected_scenes)} phân cảnh."
        if skipped > 0:
            msg += f" Bỏ qua {skipped} nhịp không tìm thấy mã ID."
            
        return msg

    def _import_unified_package(
        self,
        project: Project,
        result_data: dict[str, Any],
        episode_id: str | None,
        chapter_id: str | None = None,
    ) -> str:
        episode = self._require_episode(project, episode_id)
        total_beats = 0
        affected_scenes = 0

        # Group data by scene
        grouped_data: dict[str, list[dict]] = {}

        # 1. Support nested scenes key
        if "scenes" in result_data and isinstance(result_data["scenes"], list):
            for scene_data in result_data["scenes"]:
                sid = scene_data.get("scene_id")
                if not sid: continue
                grouped_data[sid] = scene_data.get("beats", [])

        # 2. Support flat beats key if nested is missing or empty
        if not grouped_data:
            grouped_data = self._group_beats_by_scene(result_data, "beats")

        # 3. Handle fallback to selected scene
        if len(grouped_data) == 1 and "unknown" in grouped_data and chapter_id:
            grouped_data[chapter_id] = grouped_data.pop("unknown")

        if "unknown" in grouped_data:
            raise ValueError("Không thể xác định phân cảnh cho gói dữ liệu. Vui lòng cung cấp scene_id.")

        # 4. Apply per scene
        for sid, beats in grouped_data.items():
            if not beats: continue
            
            # Ensure scene exists
            try:
                self.project_service.find_scene(project, episode.episode_id, sid)
            except LookupError:
                self.project_service.add_scene(project, episode_id=episode.episode_id, title=f"Scene {sid}", scene_id=sid)
            
            scene_gateway = _SingleResponseGateway({"beats": beats})
            scene_service = BeatGeneratorService(project_service=self.project_service, ai_gateway=scene_gateway)
            b = scene_service.generate_unified_package_for_scene(
                project, episode.episode_id, sid, use_ai=True
            )
            total_beats += len(b)
            affected_scenes += 1
        
        if total_beats > 0:
            return f"Đã nhập gói dữ liệu đầy đủ cho {total_beats} nhịp của {affected_scenes} phân cảnh."
        
        return "Không tìm thấy dữ liệu phân cảnh hợp lệ để nhập."

    def _group_beats_by_scene(self, data: dict[str, Any] | list[Any], target_key: str) -> dict[str, list[dict[str, Any]]]:
        """Group beats by scene_id from a flat structure."""
        beats = []
        if isinstance(data, list):
            beats = data
        elif isinstance(data, dict):
            beats = data.get(target_key, [])
            if not beats and "beats" in data: # Fallback
                beats = data["beats"]
        
        grouped: dict[str, list[dict[str, Any]]] = {}
        for b in beats:
            if not isinstance(b, dict): continue
            sid = b.get("scene_id", "unknown")
            if sid not in grouped: grouped[sid] = []
            grouped[sid].append(b)
        return grouped

    # ── Helpers ───────────────────────────────────────────────────

    def _group_beats_by_scene(self, result: dict[str, Any], target_key: str) -> dict[str, list[dict]]:
        """Groups flat beats by their scene_id. Returns dict {scene_id: [beats]}."""
        beats = result.get(target_key, [])
        if not isinstance(beats, list):
            return {}
            
        grouped: dict[str, list[dict]] = {}
        for b in beats:
            if not isinstance(b, dict): continue
            sid = b.get("scene_id", "unknown")
            if sid not in grouped:
                grouped[sid] = []
            grouped[sid].append(b)
        return grouped


    def _flatten_grouped_result(self, result: dict[str, Any], target_key: str) -> dict[str, Any]:
        """Convert grouped scene beats into a flat list for legacy services."""
        if target_key in result:
            return result

        flat_list = []
        if "scenes" in result and isinstance(result["scenes"], list):
            for scene in result["scenes"]:
                if "beats" in scene and isinstance(scene["beats"], list):
                    flat_list.extend(scene["beats"])

        return {target_key: flat_list}

    def _require_chapter(
        self,
        project: Project,
        chapter_id: str | None,
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
        self,
        project: Project,
        chapter_ids: list[str],
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
                f"Unsupported step '{step}'. " f"Supported: {', '.join(SUPPORTED_STEPS)}"
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
