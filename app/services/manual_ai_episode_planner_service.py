"""Manual AI episode planning with scenes, beats, and review narration."""

from __future__ import annotations

import json
import re
from typing import Any

from app.domain.beat import Beat
from app.domain.episode import ReviewEpisode
from app.domain.project import Project
from app.domain.scene import Scene
from app.domain.source_chapter import SourceChapter
from app.services.project_service import ProjectService


class ManualAIEpisodePlannerService:
    """Build and apply offline manual-AI episode package prompts."""

    LONG_CHAPTER_WORD_THRESHOLD = 1200
    LONG_CHAPTER_CHAR_THRESHOLD = 7000

    def __init__(self, project_service: ProjectService | None = None) -> None:
        self.project_service = project_service or ProjectService()

    def build_episode_plan_with_review_prompt(
        self,
        project: Project,
        source_chapter_ids: list[str],
        narration_style: str | None = None,
        retelling_density: str | None = None,
        episode_id: str | None = None,
        episode_title: str | None = None,
    ) -> str:
        chapters = self._find_chapters(project, source_chapter_ids)
        requested_density = self._normalise_density(
            retelling_density or project.retelling_density
        )
        style_preset = self._find_default_style_preset(project)
        payload = {
            "project_context": {
                "title": project.title,
                "genre": project.genre,
                "language": project.language,
                "default_narration_style": project.default_narration_style,
                "retelling_density": project.retelling_density,
                "requested_narration_style": narration_style or project.default_narration_style,
                "requested_retelling_density": requested_density,
                "density_target": self._density_target_label(requested_density),
            },
            "episode_request": {
                "episode_id": episode_id,
                "episode_title": episode_title,
                "source_chapter_ids": [chapter.chapter_id for chapter in chapters],
            },
            "source_analysis": {
                "total_word_count": sum(chapter.word_count for chapter in chapters),
                "total_character_count": sum(len(chapter.raw_text) for chapter in chapters),
                "is_long_source": self._is_long_source(chapters),
            },
            "source_chapters": [
                {
                    "chapter_id": chapter.chapter_id,
                    "title": chapter.title,
                    "chapter_number": chapter.chapter_number,
                    "raw_text": chapter.raw_text,
                    "notes": chapter.notes,
                }
                for chapter in chapters
            ],
            "character_bible": [
                self._compact_character_for_prompt(character)
                for character in project.characters
            ],
            "location_bible": [
                self._compact_location_for_prompt(location)
                for location in project.locations
            ],
            "style_context": {
                "default_art_style": project.default_art_style,
                "style_preset": self._compact_style_for_prompt(style_preset),
                "world_style_notes": project.world_style_notes,
            },
        }

        schema = {
            "episode": {
                "episode_id": "string",
                "title": "string",
                "summary": "string",
                "hook": "string",
                "cliffhanger": "string",
                "source_chapter_ids": ["string"],
                "narration_style": "string",
                "retelling_density": "string",
            },
            "scenes": [
                {
                    "scene_id": "sc_001",
                    "title": "string",
                    "summary": "string",
                    "mood": "string",
                    "characters": ["character_id"],
                    "location": "location_id",
                    "scene_type": (
                        "awakening | flashback | tragedy | conflict | discovery | "
                        "vow | reunion | transition | cliffhanger"
                    ),
                    "importance": "low | medium | high | critical",
                    "target_beats": 8,
                    "beats": [
                        {
                            "beat_id": "beat_sc_001_001",
                            "scene_id": "sc_001",
                            "order_index": 1,
                            "story_function": (
                                "hook | setup | discovery | reaction | decision | "
                                "conflict | reveal | transition | cliffhanger"
                            ),
                            "characters": ["character_id"],
                            "location": "location_id",
                            "action": "string",
                            "emotion": "string",
                            "shot_type": "string",
                            "visual_description": "string",
                            "review_text": "Vietnamese rewritten review narration",
                            "continuity_tags": ["human-readable tag name"],
                        }
                    ],
                }
            ],
        }

        return (
            "You are an expert episode planner and Vietnamese review narration writer "
            "for a comic-style story review generator.\n\n"
            "Task: analyze the selected SourceChapter raw_text, create episode "
            "screens/scenes, split each scene into beats, and write rewritten "
            "Vietnamese voice-over review_text for every beat.\n\n"
            "Beat analysis rules:\n"
            "- This is a long-form story review app, not a summary app.\n"
            "- A beat is one clear narrative moment.\n"
            "- Each beat should contain one main action, one emotional direction, "
            "one visual focus, and one story purpose.\n"
            "- One beat should be drawable as one comic/webtoon panel.\n"
            "- One beat should be suitable for one Vietnamese review_text paragraph.\n"
            "- Do not combine many major events into one beat.\n"
            "- If action changes, create a new beat.\n"
            "- If emotion changes strongly, create a new beat.\n"
            "- If location or time changes, create a new scene.\n"
            "- If the story enters a flashback, create a separate scene.\n"
            "- If a flashback covers many events, split it into many scenes and beats.\n"
            "- Every important death, loss, vow, betrayal, reunion, discovery, "
            "revelation, power breakthrough, emotional shock, and relationship "
            "change should become its own beat or group of beats.\n"
            "- Do not over-summarize.\n"
            "- Preserve story order and cause-effect.\n"
            "- Do not invent major events not supported by the source text.\n"
            "- Do not copy long source passages verbatim.\n"
            "- order_index must restart from 1 inside each scene.\n"
            "- beat_id format should be: beat_{scene_id}_{number}.\n\n"
            "Retelling density targets:\n"
            "- short: 30-45 beats for a long chapter; use only for short recap.\n"
            "- balanced: 50-70 beats for a long chapter.\n"
            "- full: 80-110 beats for a long chapter; this is the default.\n"
            "- ultra_detailed: 110-150 beats for a very dense chapter.\n"
            f"- Requested density: {requested_density} "
            f"({self._density_target_label(requested_density)}).\n\n"
            "Long chapter minimum rule:\n"
            "- For a long chapter, do not output fewer than 60 beats unless density is short.\n"
            "- For full density, aim for 80-110 beats.\n"
            "- For ultra_detailed density, aim for 110-150 beats.\n"
            "- If the source contains long backstory or life-history flashback, "
            "do not compress it into 1-3 beats.\n\n"
            "Typical target beats by scene type:\n"
            "- simple transition scene: 2-4 beats\n"
            "- normal dialogue or discovery scene: 4-7 beats\n"
            "- emotional scene: 5-8 beats\n"
            "- combat/conflict scene: 8-12 beats\n"
            "- tragedy scene: 8-12 beats\n"
            "- flashback/life-history scene: 10-15 beats\n"
            "- major backstory sequence: split into multiple scenes\n"
            "- cliffhanger scene: 2-5 beats\n\n"
            "Review text rules:\n"
            "- Each beat must include review_text.\n"
            "- review_text must be Vietnamese voice-over narration.\n"
            "- Retell the source story in detail.\n"
            "- Do not write a one-line summary.\n"
            "- Keep emotional tension.\n"
            "- Preserve cause-effect.\n"
            "- Do not copy long source passages verbatim.\n"
            "- Each review_text should be long enough to be useful for narration.\n\n"
            "Planning rules:\n"
            "- Preserve story order and cause-effect.\n"
            "- Retell in detail; do not over-summarize.\n"
            "- Do not copy long source passages verbatim.\n"
            "- Use Character Bible and Location Bible when available.\n"
            "- Create scenes/screens first; each scene needs title, summary, mood, "
            "characters, location, target_beats, and beats.\n"
            "- Each beat represents one clear narrative moment.\n"
            "- order_index must restart from 1 inside each scene.\n"
            "- scene_id must be stable.\n"
            "- beat_id should follow beat_{scene_id}_{number}.\n"
            "- Every beat must include review_text in Vietnamese.\n"
            "- Do not generate image_prompt for this task.\n"
            "- Do not generate negative_prompt for this task.\n"
            "- Return JSON only. No markdown. No explanation.\n\n"
            "Output JSON schema:\n"
            f"{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
            "Runtime input:\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )

    def apply_episode_plan_with_review_result(
        self,
        project: Project,
        result_json: str | dict[str, Any],
    ) -> dict[str, Any]:
        data = self._parse_result(result_json)
        episode_data = data.get("episode", {})
        if not isinstance(episode_data, dict):
            raise ValueError("Result field 'episode' must be an object.")

        scenes_data = data.get("scenes", [])
        if not isinstance(scenes_data, list):
            raise ValueError("Result field 'scenes' must be a list.")

        episode = self._upsert_episode(project, episode_data)
        scene_count = 0
        beat_count = 0

        for index, scene_data in enumerate(scenes_data, start=1):
            if not isinstance(scene_data, dict):
                continue
            scene = self._upsert_scene(project, episode, scene_data, index)
            scene_count += 1
            beats_data = scene_data.get("beats", [])
            if not isinstance(beats_data, list):
                continue
            for beat_index, beat_data in enumerate(beats_data, start=1):
                if not isinstance(beat_data, dict):
                    continue
                self._upsert_beat(project, episode, scene, beat_data, beat_index)
                beat_count += 1

        project.touch()
        warnings = self._density_warnings(project, episode, beat_count)
        return {
            "episode_id": episode.episode_id,
            "scene_count": scene_count,
            "beat_count": beat_count,
            "warnings": warnings,
            "message": (
                f"Đã tạo/cập nhật {scene_count} phân cảnh và "
                f"{beat_count} nhịp truyện có review text."
            ),
        }

    def _upsert_episode(self, project: Project, episode_data: dict[str, Any]) -> ReviewEpisode:
        episode_id = str(episode_data.get("episode_id") or "").strip()
        source_chapter_ids = self._as_str_list(episode_data.get("source_chapter_ids", []))
        if not source_chapter_ids and project.source_chapters:
            source_chapter_ids = [chapter.chapter_id for chapter in project.source_chapters]

        existing = None
        if episode_id:
            for episode in project.review_episodes:
                if episode.episode_id == episode_id:
                    existing = episode
                    break

        if existing is None:
            title = str(
                episode_data.get("title")
                or episode_data.get("episode_title")
                or "Manual AI Episode"
            )
            existing = self.project_service.add_review_episode(
                project,
                episode_id=episode_id or None,
                title=title,
                source_chapter_ids=source_chapter_ids,
                tone=str(
                    episode_data.get("narration_style")
                    or episode_data.get("tone")
                    or project.default_narration_style
                ),
                density=str(
                    episode_data.get("retelling_density")
                    or episode_data.get("density")
                    or project.retelling_density
                ),
                status="planned",
            )

        existing.title = str(
            episode_data.get("title")
            or episode_data.get("episode_title")
            or existing.title
        )
        existing.summary = str(
            episode_data.get("summary")
            or episode_data.get("episode_summary")
            or existing.summary
        )
        existing.hook = str(episode_data.get("hook") or existing.hook)
        existing.cliffhanger = str(episode_data.get("cliffhanger") or existing.cliffhanger)
        existing.source_chapter_ids = source_chapter_ids or list(existing.source_chapter_ids)
        existing.tone = str(
            episode_data.get("narration_style")
            or episode_data.get("tone")
            or existing.tone
        )
        existing.density = str(
            episode_data.get("retelling_density")
            or episode_data.get("density")
            or existing.density
        )
        existing.status = "planned"
        return existing

    def _upsert_scene(
        self,
        project: Project,
        episode: ReviewEpisode,
        scene_data: dict[str, Any],
        index: int,
    ) -> Scene:
        scene_id = str(scene_data.get("scene_id") or f"sc_{index:03d}")
        scene = next((item for item in episode.scenes if item.scene_id == scene_id), None)
        if scene is None:
            scene = self.project_service.add_scene(
                project,
                episode_id=episode.episode_id,
                scene_id=scene_id,
                title=str(scene_data.get("title") or f"Scene {index}"),
            )

        scene.title = str(scene_data.get("title") or scene.title)
        scene.summary = str(scene_data.get("summary") or scene.summary)
        scene.mood = str(scene_data.get("mood") or scene.mood)
        scene.characters = self._as_str_list(scene_data.get("characters", []))
        scene.location = str(scene_data.get("location") or scene.location)
        scene.importance = str(scene_data.get("importance") or scene.importance)
        if "target_beats" in scene_data:
            scene.target_beats = int(scene_data.get("target_beats") or 0)
        return scene

    def _upsert_beat(
        self,
        project: Project,
        episode: ReviewEpisode,
        scene: Scene,
        beat_data: dict[str, Any],
        beat_index: int,
    ) -> Beat:
        beat_id = str(
            beat_data.get("beat_id") or f"beat_{scene.scene_id}_{beat_index:03d}"
        )
        for other_scene in episode.scenes:
            if other_scene is scene:
                continue
            other_scene.beats = [
                beat for beat in other_scene.beats if beat.beat_id != beat_id
            ]

        beat = next((item for item in scene.beats if item.beat_id == beat_id), None)
        if beat is None:
            beat = self.project_service.add_beat(
                project,
                episode_id=episode.episode_id,
                scene_id=scene.scene_id,
                beat_id=beat_id,
                order_index=int(beat_data.get("order_index") or beat_index),
            )

        beat.scene_id = scene.scene_id
        beat.order_index = int(beat_data.get("order_index") or beat_index)
        beat.story_function = str(beat_data.get("story_function") or beat.story_function)
        beat.characters = self._as_str_list(beat_data.get("characters", []))
        beat.location = str(beat_data.get("location") or beat.location or scene.location)
        beat.action = str(beat_data.get("action") or beat.action)
        beat.emotion = str(beat_data.get("emotion") or beat.emotion)
        beat.shot_type = str(beat_data.get("shot_type") or beat.shot_type)
        beat.visual_description = str(
            beat_data.get("visual_description") or beat.visual_description
        )
        beat.review_text = str(beat_data.get("review_text") or beat.review_text)
        beat.continuity_tags = self._as_str_list(beat_data.get("continuity_tags", []))
        beat.status = "reviewed" if beat.review_text else "planned"
        return beat

    def _find_chapters(
        self,
        project: Project,
        source_chapter_ids: list[str],
    ) -> list[SourceChapter]:
        if not source_chapter_ids:
            raise ValueError("At least one source chapter must be selected.")
        chapters_by_id = {chapter.chapter_id: chapter for chapter in project.source_chapters}
        missing = [
            chapter_id for chapter_id in source_chapter_ids if chapter_id not in chapters_by_id
        ]
        if missing:
            raise LookupError("SourceChapter not found: " + ", ".join(missing))
        return [chapters_by_id[chapter_id] for chapter_id in source_chapter_ids]

    def _find_default_style_preset(self, project: Project):
        for style in project.style_presets:
            if style.style_id == project.default_art_style or style.name == project.default_art_style:
                return style
        return project.style_presets[0] if project.style_presets else None

    def _compact_character_for_prompt(self, character) -> dict[str, Any]:
        return self._drop_empty(
            {
                "character_id": character.character_id,
                "name": character.name,
                "aliases": list(character.aliases),
                "role": character.role,
                "visual_prompt_base": character.visual_prompt_base,
                "default_outfit": character.default_outfit,
                "appearance_notes": self._join_compact(
                    [
                        character.appearance,
                        character.face_details,
                        character.hair,
                        character.eyes,
                        character.body_type,
                        character.personality,
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
        return {
            key: value
            for key, value in data.items()
            if value not in (None, "", [], {})
        }

    def _join_compact(self, parts: list[str]) -> str:
        return "; ".join(
            part.strip()
            for part in parts
            if isinstance(part, str) and part.strip()
        )

    def _as_str_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value else []
        if isinstance(value, list):
            return [str(item) for item in value if item]
        return [str(value)]

    def _normalise_density(self, value: str | None) -> str:
        key = (value or "full").strip().lower().replace("-", "_").replace(" ", "_")
        if key in {"short", "condensed", "compact", "recap"}:
            return "short"
        if key in {"balanced", "medium"}:
            return "balanced"
        if key in {"detailed", "ultra", "ultra_detailed", "ultradetailed"}:
            return "ultra_detailed"
        return "full"

    def _density_target_label(self, density: str) -> str:
        targets = {
            "short": "30-45 beats for a long chapter",
            "balanced": "50-70 beats for a long chapter",
            "full": "80-110 beats for a long chapter",
            "ultra_detailed": "110-150 beats for a very dense chapter",
        }
        return targets.get(density, targets["full"])

    def _is_long_source(self, chapters: list[SourceChapter]) -> bool:
        total_words = sum(chapter.word_count for chapter in chapters)
        total_chars = sum(len(chapter.raw_text) for chapter in chapters)
        return (
            total_words >= self.LONG_CHAPTER_WORD_THRESHOLD
            or total_chars >= self.LONG_CHAPTER_CHAR_THRESHOLD
        )

    def _density_warnings(
        self,
        project: Project,
        episode: ReviewEpisode,
        beat_count: int,
    ) -> list[str]:
        chapters = self._chapters_for_episode(project, episode.source_chapter_ids)
        if not chapters or not self._is_long_source(chapters):
            return []

        density = self._normalise_density(episode.density)
        if density == "full" and beat_count < 60:
            return [
                "AI có thể đã tóm tắt quá mạnh. Chương dài ở chế độ Đầy đủ nên có khoảng 80-110 beat."
            ]
        if density == "ultra_detailed" and beat_count < 80:
            return [
                "AI có thể đã tóm tắt quá mạnh. Chương rất dày ở chế độ Siêu chi tiết nên có khoảng 110-150 beat."
            ]
        return []

    def _chapters_for_episode(
        self,
        project: Project,
        source_chapter_ids: list[str],
    ) -> list[SourceChapter]:
        chapters_by_id = {chapter.chapter_id: chapter for chapter in project.source_chapters}
        return [
            chapters_by_id[chapter_id]
            for chapter_id in source_chapter_ids
            if chapter_id in chapters_by_id
        ]

    def _parse_result(self, result_json: str | dict[str, Any]) -> dict[str, Any]:
        if isinstance(result_json, dict):
            return result_json
        cleaned = self._strip_markdown_code_block(result_json.strip())
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON result: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("Episode plan result must be a JSON object.")
        return data

    def _strip_markdown_code_block(self, text: str) -> str:
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text
