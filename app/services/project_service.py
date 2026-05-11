"""Project creation, editing, validation, and JSON persistence."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.domain.beat import Beat
from app.domain.character import Character
from app.domain.episode import ReviewEpisode
from app.domain.location import Location
from app.domain.project import SCHEMA_VERSION, Project
from app.domain.scene import Scene
from app.domain.source_chapter import SourceChapter
from app.domain.style_preset import StylePreset


class ProjectService:
    def create_project(
        self,
        title: str,
        *,
        project_id: str | None = None,
        author_source_note: str = "",
        genre: str = "",
        language: str = "vi",
        default_narration_style: str = "mysterious",
        default_art_style: str = "dark fantasy webtoon",
        retelling_density: str = "full",
    ) -> Project:
        return Project(
            project_id=project_id or "project_001",
            title=title,
            author_source_note=author_source_note,
            genre=genre,
            language=language,
            default_narration_style=default_narration_style,
            default_art_style=default_art_style,
            retelling_density=retelling_density,
        )

    def add_source_chapter(
        self,
        project: Project,
        *,
        title: str,
        chapter_number: int,
        raw_text: str,
        notes: str = "",
        chapter_id: str | None = None,
    ) -> SourceChapter:
        chapter = SourceChapter(
            chapter_id=chapter_id or self._next_id("ch", project.source_chapters),
            title=title,
            chapter_number=chapter_number,
            raw_text=raw_text,
            notes=notes,
        )
        project.source_chapters.append(chapter)
        project.touch()
        return chapter

    def add_character(
        self,
        project: Project,
        *,
        name: str,
        character_id: str | None = None,
        aliases: list[str] | None = None,
        role: str = "",
        gender: str = "",
        age_description: str = "",
        personality: str = "",
        appearance: str = "",
        face_details: str = "",
        hair: str = "",
        eyes: str = "",
        body_type: str = "",
        default_outfit: str = "",
        outfit_variants: list[str] | None = None,
        negative_prompt_terms: list[str] | None = None,
        voice_notes: str = "",
        visual_prompt_base: str = "",
        relationship_notes: str = "",
        continuity_tags: list[str] | None = None,
    ) -> Character:
        character = Character(
            character_id=character_id or self._next_id("char", project.characters),
            name=name,
            aliases=aliases or [],
            role=role,
            gender=gender,
            age_description=age_description,
            personality=personality,
            appearance=appearance,
            face_details=face_details,
            hair=hair,
            eyes=eyes,
            body_type=body_type,
            default_outfit=default_outfit,
            outfit_variants=outfit_variants or [],
            negative_prompt_terms=negative_prompt_terms or [],
            voice_notes=voice_notes,
            visual_prompt_base=visual_prompt_base,
            relationship_notes=relationship_notes,
            continuity_tags=continuity_tags or [],
        )
        project.characters.append(character)
        project.touch()
        return character

    def add_location(
        self,
        project: Project,
        *,
        name: str,
        location_id: str | None = None,
        aliases: list[str] | None = None,
        location_type: str = "",
        description: str = "",
        mood: str = "",
        time_period: str = "",
        lighting: str = "",
        color_palette: str = "",
        architecture_style: str = "",
        recurring_props: list[str] | None = None,
        visual_prompt_base: str = "",
        negative_prompt_terms: list[str] | None = None,
        continuity_tags: list[str] | None = None,
        related_scene_ids: list[str] | None = None,
    ) -> Location:
        location = Location(
            location_id=location_id or self._next_id("loc", project.locations),
            name=name,
            aliases=aliases or [],
            location_type=location_type,
            description=description,
            mood=mood,
            time_period=time_period,
            lighting=lighting,
            color_palette=color_palette,
            architecture_style=architecture_style,
            recurring_props=recurring_props or [],
            visual_prompt_base=visual_prompt_base,
            negative_prompt_terms=negative_prompt_terms or [],
            continuity_tags=continuity_tags or [],
            related_scene_ids=related_scene_ids or [],
        )
        project.locations.append(location)
        project.touch()
        return location

    def add_style_preset(
        self,
        project: Project,
        *,
        name: str,
        style_id: str | None = None,
        description: str = "",
        positive_prompt: str = "",
        negative_prompt: str = "",
        genre: str = "",
        line_style: str = "",
        color_palette: str = "",
        lighting: str = "",
        lighting_style: str = "",
        rendering_style: str = "",
        character_design_rules: str = "",
        background_detail: str = "",
        background_detail_level: str = "",
        camera_style: str = "",
        mood_keywords: list[str] | None = None,
        forbidden_terms: list[str] | None = None,
    ) -> StylePreset:
        style_preset = StylePreset(
            style_id=style_id or self._next_id("style", project.style_presets),
            name=name,
            description=description,
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
            genre=genre,
            line_style=line_style,
            color_palette=color_palette,
            lighting=lighting,
            lighting_style=lighting_style,
            rendering_style=rendering_style,
            character_design_rules=character_design_rules,
            background_detail=background_detail,
            background_detail_level=background_detail_level or background_detail,
            camera_style=camera_style,
            mood_keywords=mood_keywords or [],
            forbidden_terms=forbidden_terms or [],
        )
        project.style_presets.append(style_preset)
        project.touch()
        return style_preset

    def add_review_episode(
        self,
        project: Project,
        *,
        title: str,
        source_chapter_ids: list[str],
        episode_id: str | None = None,
        tone: str | None = None,
        density: str | None = None,
        status: str = "draft",
        summary: str = "",
        hook: str = "",
        cliffhanger: str = "",
    ) -> ReviewEpisode:
        self._ensure_source_chapters_exist(project, source_chapter_ids)
        episode = ReviewEpisode(
            episode_id=episode_id or self._next_id("ep", project.review_episodes),
            title=title,
            source_chapter_ids=source_chapter_ids,
            tone=tone or project.default_narration_style,
            density=density or project.retelling_density,
            status=status,
            summary=summary,
            hook=hook,
            cliffhanger=cliffhanger,
        )
        project.review_episodes.append(episode)
        project.touch()
        return episode

    def add_scene(
        self,
        project: Project,
        *,
        episode_id: str,
        title: str,
        scene_id: str | None = None,
        summary: str = "",
        characters: list[str] | None = None,
        location: str = "",
        mood: str = "",
        importance: str = "medium",
        target_beats: int = 0,
    ) -> Scene:
        episode = self.find_episode(project, episode_id)
        scene = Scene(
            scene_id=scene_id or self._next_scene_id(project),
            episode_id=episode.episode_id,
            title=title,
            summary=summary,
            characters=characters or [],
            location=location,
            mood=mood,
            importance=importance,
            target_beats=target_beats,
        )
        episode.scenes.append(scene)
        project.touch()
        return scene

    def add_beat(
        self,
        project: Project,
        *,
        episode_id: str,
        scene_id: str,
        beat_id: str | None = None,
        order_index: int | None = None,
        source_refs: list[str] | None = None,
        story_function: str = "",
        characters: list[str] | None = None,
        location: str = "",
        action: str = "",
        emotion: str = "",
        shot_type: str = "",
        review_text: str = "",
        visual_description: str = "",
        image_prompt: str = "",
        negative_prompt: str = "",
        continuity_tags: list[str] | None = None,
        status: str = "planned",
    ) -> Beat:
        scene = self.find_scene(project, episode_id, scene_id)
        beat = Beat(
            beat_id=beat_id or self._next_beat_id(project),
            scene_id=scene.scene_id,
            order_index=order_index if order_index is not None else len(scene.beats) + 1,
            source_refs=source_refs or [],
            story_function=story_function,
            characters=characters or [],
            location=location,
            action=action,
            emotion=emotion,
            shot_type=shot_type,
            review_text=review_text,
            visual_description=visual_description,
            image_prompt=image_prompt,
            negative_prompt=negative_prompt,
            continuity_tags=continuity_tags or [],
            status=status,
        )
        scene.beats.append(beat)
        project.touch()
        return beat

    def save_project(self, project: Project, path: str | Path) -> None:
        errors = self.validate_project(project)
        if errors:
            raise ValueError("Project validation failed: " + "; ".join(errors))

        project.touch()
        project.schema_version = SCHEMA_VERSION
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(project.to_dict(), ensure_ascii=False, indent=2) + "\n"
        self._atomic_write_text(output_path, payload)

    def load_project(self, path: str | Path) -> Project:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        data = self._migrate(data)
        project = Project.from_dict(data)
        errors = self.validate_project(project)
        if errors:
            raise ValueError("Project validation failed: " + "; ".join(errors))
        return project

    def _migrate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Upgrade ``data`` in-place from older schema versions to ``SCHEMA_VERSION``.

        Unknown / missing ``schema_version`` is treated as legacy v1.
        Future migrations should add a new ``if version < N`` block and bump
        ``SCHEMA_VERSION`` in ``app.domain.project``.
        """
        version = int(data.get("schema_version", 1))
        if version > SCHEMA_VERSION:
            raise ValueError(
                f"Project schema_version {version} is newer than this app supports "
                f"(max {SCHEMA_VERSION}). Upgrade the app to open this project."
            )
        if version < 2:
            # v1 → v2: no structural change. Just stamp the version field so
            # subsequent saves persist it explicitly.
            data["schema_version"] = 2
            version = 2
        return data

    def _atomic_write_text(self, path: Path, text: str) -> None:
        """Write ``text`` to ``path`` atomically.

        Strategy: write to a sibling ``<name>.tmp`` then ``os.replace`` it onto
        the target. This guarantees the target file either contains the full
        new payload or the previous payload — never a truncated half-write.
        """
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)

    def find_episode(self, project: Project, episode_id: str) -> ReviewEpisode:
        for episode in project.review_episodes:
            if episode.episode_id == episode_id:
                return episode
        raise LookupError(f"ReviewEpisode not found: {episode_id}")

    def find_scene(self, project: Project, episode_id: str, scene_id: str) -> Scene:
        episode = self.find_episode(project, episode_id)
        for scene in episode.scenes:
            if scene.scene_id == scene_id:
                return scene
        raise LookupError(f"Scene not found: {scene_id}")

    def validate_project(self, project: Project) -> list[str]:
        errors: list[str] = []
        chapter_ids = {chapter.chapter_id for chapter in project.source_chapters}

        for episode in project.review_episodes:
            for chapter_id in episode.source_chapter_ids:
                if chapter_id not in chapter_ids:
                    errors.append(
                        f"{episode.episode_id} references missing source chapter " f"{chapter_id}"
                    )

            for scene in episode.scenes:
                if scene.episode_id != episode.episode_id:
                    errors.append(
                        f"{scene.scene_id} has episode_id {scene.episode_id}, "
                        f"expected {episode.episode_id}"
                    )

                seen_order_indexes: set[int] = set()
                for beat in scene.beats:
                    if beat.scene_id != scene.scene_id:
                        errors.append(
                            f"{beat.beat_id} has scene_id {beat.scene_id}, "
                            f"expected {scene.scene_id}"
                        )
                    if beat.order_index in seen_order_indexes:
                        errors.append(
                            f"{scene.scene_id} has duplicate beat order " f"{beat.order_index}"
                        )
                    seen_order_indexes.add(beat.order_index)

        return errors

    def _ensure_source_chapters_exist(
        self, project: Project, source_chapter_ids: list[str]
    ) -> None:
        existing_ids = {chapter.chapter_id for chapter in project.source_chapters}
        missing_ids = [
            chapter_id for chapter_id in source_chapter_ids if chapter_id not in existing_ids
        ]
        if missing_ids:
            raise LookupError("SourceChapter not found: " + ", ".join(missing_ids))

    def _next_scene_id(self, project: Project) -> str:
        scenes = [scene for episode in project.review_episodes for scene in episode.scenes]
        return self._next_id("sc", scenes)

    def _next_beat_id(self, project: Project) -> str:
        beats = [
            beat
            for episode in project.review_episodes
            for scene in episode.scenes
            for beat in scene.beats
        ]
        return self._next_id("b", beats)

    def _next_id(self, prefix: str, existing_items: list[Any]) -> str:
        id_attribute_by_prefix = {
            "b": "beat_id",
            "ch": "chapter_id",
            "char": "character_id",
            "ep": "episode_id",
            "loc": "location_id",
            "sc": "scene_id",
            "style": "style_id",
        }
        id_attribute = id_attribute_by_prefix[prefix]
        max_number = 0

        for item in existing_items:
            item_id = getattr(item, id_attribute)
            parts = item_id.rsplit("_", 1)
            if len(parts) == 2 and parts[0] == prefix and parts[1].isdigit():
                max_number = max(max_number, int(parts[1]))

        return f"{prefix}_{max_number + 1:03d}"
