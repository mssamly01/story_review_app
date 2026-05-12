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
from app.services.manual_ai_episode_planner_service import ManualAIEpisodePlannerService
from app.services.project_service import ProjectService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.review_rewriter_service import ReviewRewriterService
from app.services.story_parser_service import StoryParserService

SUPPORTED_STEPS = [
    "parse-story",
    "plan-episode",
    "plan-episode-with-review",
    "generate-beats",
    "rewrite-review",
    "build-prompts",
    "generate-unified-package",
]

_STEP_TO_PROMPT_NAME = {
    "parse-story": "story_parser",
    "plan-episode": "episode_planner",
    "plan-episode-with-review": "episode_planner",
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
        chapter_ids: list[str] | None = None,
        episode_id: str | None = None,
        episode_title: str | None = None,
        tone: str | None = None,
        density: str | None = None,
        style_preset_id: str | None = None,
    ) -> dict[str, Any]:
        """Trả về dict chứa prompt_template + input_data + output_schema."""
        self._validate_step(step)
        if step == "plan-episode-with-review":
            selected_chapter_ids = chapter_ids or ([chapter_id] if chapter_id else [])
            prompt_text = ManualAIEpisodePlannerService(
                self.project_service
            ).build_episode_plan_with_review_prompt(
                project,
                source_chapter_ids=selected_chapter_ids,
                narration_style=tone,
                retelling_density=density,
                episode_id=episode_id,
                episode_title=episode_title,
            )
            return {
                "step": step,
                "prompt_name": "episode_plan_with_review",
                "prompt_text": prompt_text,
                "prompt_template": prompt_text,
                "input_data": {},
            }

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
        if exported.get("prompt_text"):
            return str(exported["prompt_text"])

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
        chapter_ids: list[str] | None = None,
        episode_id: str | None = None,
        tone: str | None = None,
        density: str | None = None,
        style_preset_id: str | None = None,
    ) -> str:
        """Áp dụng AI result vào project. Trả về summary message."""
        self._validate_step(step)

        if step == "plan-episode-with-review":
            summary = ManualAIEpisodePlannerService(
                self.project_service
            ).apply_episode_plan_with_review_result(project, result_data)
            message = str(summary["message"])
            warnings = summary.get("warnings", [])
            if warnings:
                message += "\n" + "\n".join(str(item) for item in warnings)
            return message

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
            "character_bible": [
                self._compact_character_for_prompt(character)
                for character in project.characters
            ],
            "location_bible": [
                self._compact_location_for_prompt(location)
                for location in project.locations
            ],
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
            "source_chapters": [self._compact_source_chapter_for_prompt(chapter)],
            "narration_style": tone or project.default_narration_style,
            "retelling_density": density or project.retelling_density,
            "character_bible": [
                self._compact_character_for_prompt(character)
                for character in project.characters
            ],
            "location_bible": [
                self._compact_location_for_prompt(location)
                for location in project.locations
            ],
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
            "episode": self._compact_episode_for_prompt(episode),
            "source_chapters": [
                self._compact_source_chapter_for_prompt(chapter)
                for chapter in source_chapters
            ],
            "scenes": [
                self._compact_scene_for_prompt(scene, len(scene.ordered_beats()))
                for scene in episode.scenes
            ],
            "retelling_density": density or episode.density,
            "character_bible": [
                self._compact_character_for_prompt(character)
                for character in project.characters
            ],
            "location_bible": [
                self._compact_location_for_prompt(location)
                for location in project.locations
            ],
            "style_preset": self._compact_style_for_prompt(
                self._find_style_preset(project, project.default_art_style)
            ),
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
            ordered_beats = scene.ordered_beats()
            scenes_input.append(
                {
                    "scene": self._compact_scene_for_prompt(scene, len(ordered_beats)),
                    "beats": [
                        self._compact_beat_for_prompt(beat, include_review_excerpt=False)
                        for beat in ordered_beats
                    ],
                    "narration_style": tone or episode.tone,
                    "retelling_density": density or episode.density,
                }
            )
        return {
            "episode_id": episode.episode_id,
            "episode_title": episode.title,
            "source_chapter_context": [
                self._compact_source_chapter_for_prompt(chapter)
                for chapter in source_chapters
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

        used_character_ids: set[str] = set()
        used_location_ids: set[str] = set()
        scenes_input = []
        for scene in episode.scenes:
            ordered_beats = scene.ordered_beats()
            used_character_ids.update(scene.characters)
            if scene.location:
                used_location_ids.add(scene.location)
            for beat in ordered_beats:
                used_character_ids.update(beat.characters)
                if beat.location:
                    used_location_ids.add(beat.location)

            scenes_input.append(
                {
                    "scene": self._compact_scene_for_prompt(scene, len(ordered_beats)),
                    "beats": [self._compact_beat_for_prompt(beat) for beat in ordered_beats],
                }
            )

        characters = [
            self._compact_character_for_prompt(character)
            for character in project.characters
            if not used_character_ids
            or character.character_id in used_character_ids
            or character.name in used_character_ids
        ]
        locations = [
            self._compact_location_for_prompt(location)
            for location in project.locations
            if not used_location_ids
            or location.location_id in used_location_ids
            or location.name in used_location_ids
        ]

        return {
            "episode_id": episode.episode_id,
            "episode_title": episode.title,
            "task": "build concise English image prompts for existing beats only",
            "prompt_length_guidance": "Use only the compact context below. Aim for 45-90 words per image_prompt.",
            "character_bible": characters,
            "location_bible": locations,
            "style_preset": self._compact_style_for_prompt(style_preset),
            "scenes": scenes_input,
        }

    def _compact_scene_for_prompt(self, scene, beat_count: int) -> dict[str, Any]:
        return self._drop_empty(
            {
                "scene_id": scene.scene_id,
                "title": scene.title,
                "summary": scene.summary,
                "mood": scene.mood,
                "characters": list(scene.characters),
                "location": scene.location,
                "importance": scene.importance,
                "target_beats": scene.target_beats,
                "beat_count": beat_count,
            }
        )

    def _compact_episode_for_prompt(self, episode) -> dict[str, Any]:
        return self._drop_empty(
            {
                "episode_id": episode.episode_id,
                "title": episode.title,
                "summary": episode.summary,
                "source_chapter_ids": list(episode.source_chapter_ids),
                "tone": episode.tone,
                "density": episode.density,
                "hook": episode.hook,
                "cliffhanger": episode.cliffhanger,
                "scene_count": len(episode.scenes),
            }
        )

    def _compact_source_chapter_for_prompt(self, chapter) -> dict[str, Any]:
        return self._drop_empty(
            {
                "chapter_id": chapter.chapter_id,
                "title": chapter.title,
                "chapter_number": chapter.chapter_number,
                "word_count": chapter.word_count,
                "raw_text": chapter.raw_text,
                "notes": chapter.notes,
            }
        )

    def _compact_beat_for_prompt(
        self,
        beat,
        *,
        include_review_excerpt: bool = True,
    ) -> dict[str, Any]:
        data = {
            "beat_id": beat.beat_id,
            "scene_id": beat.scene_id,
            "order_index": beat.order_index,
            "story_function": beat.story_function,
            "characters": list(beat.characters),
            "location": beat.location,
            "action": beat.action,
            "emotion": beat.emotion,
            "shot_type": beat.shot_type,
            "visual_description": beat.visual_description,
            "continuity_tags": list(beat.continuity_tags),
        }
        if include_review_excerpt:
            data["review_text_excerpt"] = self._shorten(beat.review_text, 260)
        return self._drop_empty(
            data
        )

    def _compact_character_for_prompt(self, character) -> dict[str, Any]:
        return self._drop_empty(
            {
                "character_id": character.character_id,
                "name": character.name,
                "aliases": list(character.aliases),
                "visual_prompt_base": character.visual_prompt_base,
                "default_outfit": character.default_outfit,
                "appearance_notes": self._join_compact(
                    [
                        character.appearance,
                        character.face_details,
                        character.hair,
                        character.eyes,
                        character.body_type,
                        character.signature_features,
                        character.continuity_must_keep,
                    ]
                ),
                "negative_prompt_terms": list(character.negative_prompt_terms),
            }
        )

    def _compact_location_for_prompt(self, location) -> dict[str, Any]:
        return self._drop_empty(
            {
                "location_id": location.location_id,
                "name": location.name,
                "aliases": list(location.aliases),
                "visual_prompt_base": location.visual_prompt_base,
                "mood": location.mood,
                "lighting": location.lighting,
                "setting_notes": self._join_compact(
                    [
                        location.location_type,
                        location.description,
                        location.architecture_style,
                        ", ".join(location.recurring_props),
                        location.color_palette,
                    ]
                ),
                "negative_prompt_terms": list(location.negative_prompt_terms),
            }
        )

    def _compact_style_for_prompt(self, style_preset) -> dict[str, Any]:
        if not style_preset:
            return {}
        return self._drop_empty(
            {
                "style_id": style_preset.style_id,
                "name": style_preset.name,
                "positive_prompt": style_preset.positive_prompt,
                "negative_prompt": style_preset.negative_prompt,
                "forbidden_terms": list(style_preset.forbidden_terms),
                "lighting_style": style_preset.lighting_style,
                "color_palette": style_preset.color_palette,
                "character_design_rules": style_preset.character_design_rules,
            }
        )

    def _drop_empty(self, data: dict[str, Any]) -> dict[str, Any]:
        cleaned: dict[str, Any] = {}
        for key, value in data.items():
            if value in (None, "", [], {}):
                continue
            cleaned[key] = value
        return cleaned

    def _join_compact(self, parts: list[str]) -> str:
        return "; ".join(part.strip() for part in parts if isinstance(part, str) and part.strip())

    def _shorten(self, value: str, limit: int) -> str:
        text = " ".join(value.split())
        if len(text) <= limit:
            return text
        return text[: limit - 1].rstrip() + "..."

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
            "episode": self._compact_episode_for_prompt(episode),
            "scenes": [
                {
                    "scene": self._compact_scene_for_prompt(
                        scene,
                        len(scene.ordered_beats()),
                    ),
                    "beats": [
                        self._compact_beat_for_prompt(
                            beat,
                            include_review_excerpt=False,
                        )
                        for beat in scene.ordered_beats()
                    ],
                }
                for scene in episode.scenes
            ],
            "source_chapters": [
                self._compact_source_chapter_for_prompt(chapter)
                for chapter in source_chapters
            ],
            "character_bible": [
                self._compact_character_for_prompt(character)
                for character in project.characters
            ],
            "location_bible": [
                self._compact_location_for_prompt(location)
                for location in project.locations
            ],
            "style_preset": self._compact_style_for_prompt(style_preset),
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
        
        # 3. If still unknown and no selection, skip those beats for whole-episode import.
        grouped.pop("unknown", None)

        total_beats = 0
        affected_scenes = 0

        for sid, beats in grouped.items():
            if not beats: continue
            
            try:
                self.project_service.find_scene(project, episode.episode_id, sid)
            except LookupError:
                continue
            
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
        
        return "Không tìm thấy dữ liệu phân cảnh hợp lệ để nhập. 0 beats imported."

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
        """Groups flat or nested scene beats by their scene_id."""
        beats = result.get(target_key, [])
        if not beats and isinstance(result.get("scenes"), list):
            beats = []
            for scene_data in result["scenes"]:
                if not isinstance(scene_data, dict):
                    continue
                scene_id = scene_data.get("scene_id")
                for beat in scene_data.get("beats", []):
                    if isinstance(beat, dict):
                        item = dict(beat)
                        if scene_id and not item.get("scene_id"):
                            item["scene_id"] = scene_id
                        beats.append(item)
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
