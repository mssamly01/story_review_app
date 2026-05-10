"""Export project and episode data into user-facing formats."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from app.domain.beat import Beat
from app.domain.character import Character
from app.domain.episode import ReviewEpisode
from app.domain.location import Location
from app.domain.project import Project
from app.domain.scene import Scene
from app.domain.style_preset import StylePreset
from app.services.project_service import ProjectService


class ExportService:
    CSV_COLUMNS = [
        "episode_id",
        "episode_title",
        "scene_id",
        "scene_title",
        "beat_id",
        "order_index",
        "story_function",
        "characters",
        "location",
        "action",
        "emotion",
        "shot_type",
        "review_text",
        "visual_description",
        "image_prompt",
        "negative_prompt",
        "continuity_tags",
    ]

    def __init__(self, project_service: ProjectService | None = None) -> None:
        self.project_service = project_service or ProjectService()

    def export_episode_markdown(self, project: Project, episode_id: str) -> str:
        episode = self.project_service.find_episode(project, episode_id)
        lines = [
            f"# {episode.title}",
            "",
            f"- Project title: {project.title}",
            f"- Episode ID: `{episode.episode_id}`",
            f"- Tone: {episode.tone}",
            f"- Density: {episode.density}",
            f"- Source chapters: {', '.join(episode.source_chapter_ids)}",
        ]

        if episode.hook:
            lines.extend(["", f"Hook: {episode.hook}"])
        if episode.summary:
            lines.extend(["", f"Summary: {episode.summary}"])

        for scene_index, scene in enumerate(self._ordered_scenes(episode), start=1):
            lines.extend(
                [
                    "",
                    f"## Scene {scene_index} - {scene.title}",
                    "",
                    f"- Scene ID: `{scene.scene_id}`",
                    f"- Characters: {', '.join(scene.characters)}",
                    f"- Mood: {scene.mood}",
                    f"- Location: {scene.location}",
                ]
            )
            if scene.summary:
                lines.extend(["", scene.summary])

            for beat in scene.ordered_beats():
                lines.extend(self._beat_markdown(beat))

        if episode.cliffhanger:
            lines.extend(["", "## Cliffhanger", "", episode.cliffhanger])

        return "\n".join(lines).rstrip() + "\n"

    def export_episode_to_markdown(
        self, project: Project, episode_id: str
    ) -> str:
        return self.export_episode_markdown(project, episode_id)

    def export_episode_json(
        self, project: Project, episode_id: str
    ) -> dict[str, Any]:
        episode = self.project_service.find_episode(project, episode_id)
        character_ids = self._used_character_ids(episode)
        location_ids = self._used_location_ids(episode)
        style_preset = self._selected_style_preset(project)

        return {
            "project": {
                "project_id": project.project_id,
                "title": project.title,
                "genre": project.genre,
                "language": project.language,
                "default_narration_style": project.default_narration_style,
                "default_art_style": project.default_art_style,
                "retelling_density": project.retelling_density,
            },
            "episode": {
                "episode_id": episode.episode_id,
                "title": episode.title,
                "source_chapter_ids": list(episode.source_chapter_ids),
                "tone": episode.tone,
                "density": episode.density,
                "status": episode.status,
                "summary": episode.summary,
                "hook": episode.hook,
                "cliffhanger": episode.cliffhanger,
                "scene_ids": [
                    scene.scene_id for scene in self._ordered_scenes(episode)
                ],
                "estimated_beats": episode.estimated_beats,
            },
            "scenes": [
                self._scene_export_dict(scene)
                for scene in self._ordered_scenes(episode)
            ],
            "beats": [
                beat.to_dict()
                for scene in self._ordered_scenes(episode)
                for beat in self._ordered_beats(scene)
            ],
            "characters_used": list(character_ids),
            "locations_used": list(location_ids),
            "characters": [
                character.to_dict()
                for character in self._characters_by_id(project, character_ids)
            ],
            "locations": [
                location.to_dict()
                for location in self._locations_by_id(project, location_ids)
            ],
            "style_preset": (
                style_preset.to_dict() if style_preset is not None else None
            ),
        }

    def export_episode_csv(self, project: Project, episode_id: str) -> str:
        episode = self.project_service.find_episode(project, episode_id)
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=self.CSV_COLUMNS,
            lineterminator="\n",
        )
        writer.writeheader()

        for scene in self._ordered_scenes(episode):
            for beat in self._ordered_beats(scene):
                writer.writerow(self._beat_csv_row(episode, scene, beat))

        return output.getvalue()

    def export_review_script_txt(
        self, project: Project, episode_id: str
    ) -> str:
        episode = self.project_service.find_episode(project, episode_id)
        lines = [episode.title]

        for scene_index, scene in enumerate(self._ordered_scenes(episode), start=1):
            lines.extend(["", f"Scene {scene_index}: {scene.title}"])
            for beat in self._ordered_beats(scene):
                if beat.review_text:
                    lines.extend(["", beat.review_text])

        return "\n".join(lines).rstrip() + "\n"

    def export_image_prompts_txt(
        self, project: Project, episode_id: str
    ) -> str:
        episode = self.project_service.find_episode(project, episode_id)
        lines = [episode.title]

        for scene_index, scene in enumerate(self._ordered_scenes(episode), start=1):
            lines.extend(["", f"Scene {scene_index}: {scene.title}"])
            for beat in self._ordered_beats(scene):
                lines.extend(
                    [
                        "",
                        f"Beat ID: {beat.beat_id}",
                        "Image prompt:",
                        beat.image_prompt or "_Not generated yet._",
                        "Negative prompt:",
                        beat.negative_prompt or "_Not generated yet._",
                    ]
                )

        return "\n".join(lines).rstrip() + "\n"

    def write_text_file(self, content: str, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_json_file(
        self, data: dict[str, Any], output_path: str | Path
    ) -> Path:
        return self.write_text_file(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            output_path,
        )

    def save_episode_markdown(
        self, project: Project, episode_id: str, path: str | Path
    ) -> None:
        self.write_text_file(self.export_episode_markdown(project, episode_id), path)

    def _beat_markdown(self, beat: Beat) -> list[str]:
        lines = [
            "",
            f"### Beat {beat.order_index} - `{beat.beat_id}`",
            "",
            f"- Story function: {beat.story_function}",
            f"- Characters: {', '.join(beat.characters)}",
            f"- Location: {beat.location}",
            f"- Action: {beat.action}",
            f"- Emotion: {beat.emotion}",
            f"- Shot type: {beat.shot_type}",
        ]

        if beat.continuity_tags:
            lines.append(
                f"- Continuity tags: {', '.join(beat.continuity_tags)}"
            )

        lines.extend(["", "Review text:", beat.review_text or "_Not written yet._"])

        if beat.visual_description:
            lines.extend(["", "Visual description:", beat.visual_description])

        lines.extend(["", "Image prompt:", beat.image_prompt or "_Not generated yet._"])

        if beat.negative_prompt:
            lines.extend(["", "Negative prompt:", beat.negative_prompt])

        return lines

    def _scene_export_dict(self, scene: Scene) -> dict[str, Any]:
        return {
            "scene_id": scene.scene_id,
            "episode_id": scene.episode_id,
            "title": scene.title,
            "summary": scene.summary,
            "characters": list(scene.characters),
            "location": scene.location,
            "mood": scene.mood,
            "importance": scene.importance,
            "target_beats": scene.target_beats,
            "beat_ids": scene.beat_ids,
            "beats": [beat.to_dict() for beat in self._ordered_beats(scene)],
        }

    def _beat_csv_row(
        self, episode: ReviewEpisode, scene: Scene, beat: Beat
    ) -> dict[str, str | int]:
        return {
            "episode_id": episode.episode_id,
            "episode_title": episode.title,
            "scene_id": scene.scene_id,
            "scene_title": scene.title,
            "beat_id": beat.beat_id,
            "order_index": beat.order_index,
            "story_function": beat.story_function,
            "characters": "|".join(beat.characters),
            "location": beat.location,
            "action": beat.action,
            "emotion": beat.emotion,
            "shot_type": beat.shot_type,
            "review_text": beat.review_text,
            "visual_description": beat.visual_description,
            "image_prompt": beat.image_prompt,
            "negative_prompt": beat.negative_prompt,
            "continuity_tags": "|".join(beat.continuity_tags),
        }

    def _ordered_scenes(self, episode: ReviewEpisode) -> list[Scene]:
        return list(episode.scenes)

    def _ordered_beats(self, scene: Scene) -> list[Beat]:
        return scene.ordered_beats()

    def _used_character_ids(self, episode: ReviewEpisode) -> list[str]:
        character_ids: list[str] = []
        for scene in self._ordered_scenes(episode):
            for character_id in scene.characters:
                self._append_unique(character_ids, character_id)
            for beat in self._ordered_beats(scene):
                for character_id in beat.characters:
                    self._append_unique(character_ids, character_id)
        return character_ids

    def _used_location_ids(self, episode: ReviewEpisode) -> list[str]:
        location_ids: list[str] = []
        for scene in self._ordered_scenes(episode):
            self._append_unique(location_ids, scene.location)
            for beat in self._ordered_beats(scene):
                self._append_unique(location_ids, beat.location)
        return [location_id for location_id in location_ids if location_id]

    def _characters_by_id(
        self, project: Project, character_ids: list[str]
    ) -> list[Character]:
        by_id = {
            character.character_id: character for character in project.characters
        }
        return [
            by_id[character_id]
            for character_id in character_ids
            if character_id in by_id
        ]

    def _locations_by_id(
        self, project: Project, location_ids: list[str]
    ) -> list[Location]:
        by_id = {location.location_id: location for location in project.locations}
        return [
            by_id[location_id]
            for location_id in location_ids
            if location_id in by_id
        ]

    def _selected_style_preset(self, project: Project) -> StylePreset | None:
        if not project.style_presets:
            return None

        preferred = self._normalise_key(project.default_art_style)
        for style_preset in project.style_presets:
            if self._normalise_key(style_preset.style_id) == preferred:
                return style_preset
            if self._normalise_key(style_preset.name) == preferred:
                return style_preset

        return project.style_presets[0]

    def _append_unique(self, values: list[str], value: str) -> None:
        if value and value not in values:
            values.append(value)

    def _normalise_key(self, value: str) -> str:
        return "_".join(value.lower().split())
