"""Deterministic beat planning service.

This service converts planned scenes into structured Beat objects. It also
exposes ``generate_unified_package_for_*`` methods that chain beat generation,
review rewriting, and image-prompt building in one call — the equivalent of
the (now removed) ``BeatPackageGeneratorService``.
"""

from __future__ import annotations

import re
from typing import Any

from app.domain.beat import Beat
from app.domain.episode import ReviewEpisode
from app.domain.project import Project
from app.domain.scene import Scene
from app.domain.source_chapter import SourceChapter
from app.infrastructure.ai_gateway import AIGateway
from app.services.project_service import ProjectService


class BeatGeneratorService:
    _allowed_retelling_densities = {"full", "balanced", "condensed"}
    _base_beat_counts = {
        "full": 6,
        "balanced": 4,
        "condensed": 2,
    }
    _target_multipliers = {
        "full": 1.0,
        "balanced": 0.75,
        "condensed": 0.5,
    }
    _importance_bonus = {
        "high": 2,
        "medium": 1,
        "low": 0,
    }
    _story_functions = [
        "hook",
        "setup",
        "discovery",
        "reaction",
        "decision",
        "conflict",
        "reveal",
        "transition",
        "cliffhanger",
    ]
    _shot_types = [
        "establishing shot",
        "wide shot",
        "medium shot",
        "close-up",
        "detail shot",
        "over-the-shoulder shot",
        "low angle shot",
        "high angle shot",
        "extreme close-up",
    ]
    _default_emotions = [
        "curious",
        "tense",
        "confused",
        "determined",
        "suspicious",
        "shocked",
        "calm",
    ]
    _emotion_keywords = {
        "lonely": "sad",
        "mysterious": "suspicious",
        "tense": "tense",
        "dramatic": "shocked",
        "angry": "angry",
        "fear": "fearful",
    }

    def __init__(
        self,
        project_service: ProjectService | None = None,
        ai_gateway: AIGateway | None = None,
        use_ai: bool = False,
    ) -> None:
        self.project_service = project_service or ProjectService()
        self.ai_gateway = ai_gateway
        self.use_ai = use_ai

    def generate_beats_for_scene(
        self,
        project: Project,
        episode_id: str,
        scene_id: str,
        retelling_density: str | None = None,
    ) -> list[Beat]:
        episode = self.project_service.find_episode(project, episode_id)
        scene = self.project_service.find_scene(project, episode_id, scene_id)
        density = retelling_density or episode.density
        self._validate_density(density)

        source_chapters = self._source_chapters_for_episode(project, episode_id)
        preserved_beats = [
            beat
            for beat in scene.beats
            if not beat.beat_id.startswith(self._generated_prefix(scene.scene_id))
        ]
        if self.use_ai:
            generated_beats = self._build_beats_with_ai(
                project=project,
                episode_id=episode_id,
                scene=scene,
                source_chapters=source_chapters,
                retelling_density=density,
                starting_order_index=len(preserved_beats) + 1,
            )
        else:
            generated_beats = self._build_beats(
                episode_id=episode_id,
                scene=scene,
                source_chapters=source_chapters,
                retelling_density=density,
                starting_order_index=len(preserved_beats) + 1,
            )
        scene.beats = preserved_beats + generated_beats
        project.touch()
        return generated_beats

    def generate_beats_for_episode(
        self,
        project: Project,
        episode_id: str,
        retelling_density: str | None = None,
    ) -> list[Beat]:
        episode = self.project_service.find_episode(project, episode_id)
        density = retelling_density or episode.density
        self._validate_density(density)

        generated_beats: list[Beat] = []
        for scene in episode.scenes:
            generated_beats.extend(
                self.generate_beats_for_scene(
                    project,
                    episode_id,
                    scene.scene_id,
                    density,
                )
            )
        return generated_beats

    def generate_unified_package_for_scene(
        self,
        project: Project,
        episode_id: str,
        scene_id: str,
        narration_style: str | None = None,
        retelling_density: str | None = None,
        style_preset_id: str | None = None,
        use_ai: bool = False,
    ) -> list[Beat]:
        """Generate beats + review narration + image prompts for one scene.

        Replaces the standalone BeatPackageGeneratorService. By default chains
        the three single-responsibility services deterministically; with
        ``use_ai=True`` issues a single unified AI call via the
        ``beat_package_generator`` prompt template.
        """
        episode = self.project_service.find_episode(project, episode_id)
        scene = self.project_service.find_scene(project, episode_id, scene_id)

        if use_ai:
            return self._generate_unified_package_with_ai(
                project=project,
                episode=episode,
                scene=scene,
                narration_style=narration_style,
                retelling_density=retelling_density,
                style_preset_id=style_preset_id,
            )
        return self._generate_unified_package_deterministic(
            project=project,
            episode_id=episode_id,
            scene=scene,
            narration_style=narration_style,
            retelling_density=retelling_density,
            style_preset_id=style_preset_id,
        )

    def generate_unified_package_for_episode(
        self,
        project: Project,
        episode_id: str,
        narration_style: str | None = None,
        retelling_density: str | None = None,
        style_preset_id: str | None = None,
        use_ai: bool = False,
    ) -> list[Beat]:
        episode = self.project_service.find_episode(project, episode_id)
        all_beats: list[Beat] = []
        for scene in episode.scenes:
            all_beats.extend(
                self.generate_unified_package_for_scene(
                    project=project,
                    episode_id=episode_id,
                    scene_id=scene.scene_id,
                    narration_style=narration_style,
                    retelling_density=retelling_density,
                    style_preset_id=style_preset_id,
                    use_ai=use_ai,
                )
            )
        return all_beats

    def _generate_unified_package_deterministic(
        self,
        *,
        project: Project,
        episode_id: str,
        scene: Scene,
        narration_style: str | None,
        retelling_density: str | None,
        style_preset_id: str | None,
    ) -> list[Beat]:
        from app.services.prompt_builder_service import PromptBuilderService
        from app.services.review_rewriter_service import ReviewRewriterService

        self.generate_beats_for_scene(project, episode_id, scene.scene_id, retelling_density)
        ReviewRewriterService(ai_gateway=self.ai_gateway, use_ai=False).rewrite_scene(
            project, scene.scene_id, narration_style, retelling_density
        )
        PromptBuilderService(ai_gateway=self.ai_gateway, use_ai=False).build_prompts_for_scene(
            project, scene.scene_id, style_preset_id
        )
        return scene.beats

    def _generate_unified_package_with_ai(
        self,
        *,
        project: Project,
        episode: ReviewEpisode,
        scene: Scene,
        narration_style: str | None,
        retelling_density: str | None,
        style_preset_id: str | None,
    ) -> list[Beat]:
        gateway = self._require_ai_gateway()

        style_preset = None
        target_style_id = style_preset_id or project.default_art_style
        for preset in project.style_presets:
            if preset.style_id == target_style_id or preset.name == target_style_id:
                style_preset = preset
                break

        chapters_by_id = {c.chapter_id: c for c in project.source_chapters}
        source_chapters = [
            chapters_by_id[cid] for cid in episode.source_chapter_ids if cid in chapters_by_id
        ]

        input_data = {
            "project_genre": project.genre,
            "style_preset_name": style_preset.name if style_preset else "Default",
            "style_positive": style_preset.positive_prompt if style_preset else "",
            "style_negative": style_preset.negative_prompt if style_preset else "",
            "narration_style": narration_style or episode.tone,
            "retelling_density": retelling_density or episode.density,
            "character_bible": [c.to_dict() for c in project.characters],
            "location_bible": [loc.to_dict() for loc in project.locations],
            "episode_title": episode.title,
            "episode_summary": episode.summary,
            "scene_title": scene.title,
            "scene_summary": scene.summary,
            "source_text": "\n".join(c.raw_text for c in source_chapters),
        }

        response = gateway.generate_json("beat_package_generator", input_data)
        beats_data = response.get("beats", [])

        preserved_beats = [
            beat
            for beat in scene.beats
            if not beat.beat_id.startswith(self._generated_prefix(scene.scene_id))
        ]

        new_beats: list[Beat] = []
        for i, b_data in enumerate(beats_data):
            beat_id = f"beat_{scene.scene_id}_{i + 1:03d}"
            new_beats.append(
                Beat(
                    beat_id=beat_id,
                    scene_id=scene.scene_id,
                    order_index=len(preserved_beats) + i + 1,
                    source_refs=[c.chapter_id for c in source_chapters],
                    story_function=str(b_data.get("story_function", "")),
                    characters=[str(c) for c in b_data.get("characters", [])],
                    location=str(b_data.get("location", "")),
                    action=str(b_data.get("action", "")),
                    emotion=str(b_data.get("emotion", "")),
                    shot_type=str(b_data.get("shot_type", "")),
                    visual_description=str(b_data.get("visual_description", "")),
                    review_text=str(b_data.get("review_text", "")),
                    image_prompt=str(b_data.get("image_prompt", "")),
                    negative_prompt=str(b_data.get("negative_prompt", "")),
                    continuity_tags=[str(t) for t in b_data.get("continuity_tags", [])],
                    status="planned",
                )
            )

        scene.beats = preserved_beats + new_beats
        project.touch()
        return new_beats

    def _build_beats(
        self,
        *,
        episode_id: str,
        scene: Scene,
        source_chapters: list[SourceChapter],
        retelling_density: str,
        starting_order_index: int,
    ) -> list[Beat]:
        beat_count = self._beat_count_for_scene(scene, retelling_density)
        moments = self._extract_scene_moments(scene)
        source_refs = [chapter.chapter_id for chapter in source_chapters]
        generated_beats: list[Beat] = []

        for offset in range(beat_count):
            beat_index = offset + 1
            story_function = self._story_function_for_index(beat_index, beat_count)
            moment = moments[offset % len(moments)]
            shot_type = self._shot_types[offset % len(self._shot_types)]
            emotion = self._emotion_for_scene(scene, offset)
            beat_id = f"{self._generated_prefix(scene.scene_id)}{beat_index:03d}"

            generated_beats.append(
                Beat(
                    beat_id=beat_id,
                    scene_id=scene.scene_id,
                    order_index=starting_order_index + offset,
                    source_refs=source_refs,
                    story_function=story_function,
                    characters=list(scene.characters),
                    location=scene.location,
                    action=self._build_action(story_function, moment),
                    emotion=emotion,
                    shot_type=shot_type,
                    visual_description=self._build_visual_description(
                        scene=scene,
                        moment=moment,
                        emotion=emotion,
                        shot_type=shot_type,
                    ),
                    review_text="",
                    image_prompt="",
                    negative_prompt="",
                    continuity_tags=self._build_continuity_tags(
                        episode_id=episode_id,
                        scene=scene,
                        source_refs=source_refs,
                        retelling_density=retelling_density,
                    ),
                    status="planned",
                )
            )

        return generated_beats

    def _build_beats_with_ai(
        self,
        *,
        project: Project,
        episode_id: str,
        scene: Scene,
        source_chapters: list[SourceChapter],
        retelling_density: str,
        starting_order_index: int,
    ) -> list[Beat]:
        gateway = self._require_ai_gateway()
        response = gateway.generate_json(
            "beat_generator",
            {
                "episode_id": episode_id,
                "scene_id": scene.scene_id,
                "scene": scene.to_dict(),
                "source_chapter_context": [
                    {
                        "chapter_id": chapter.chapter_id,
                        "title": chapter.title,
                        "raw_text": chapter.raw_text,
                    }
                    for chapter in source_chapters
                ],
                "retelling_density": retelling_density,
                "character_bible": [character.to_dict() for character in project.characters],
                "location_bible": [location.to_dict() for location in project.locations],
            },
        )
        beats_data = self._ai_beats_data(response)
        source_refs = [chapter.chapter_id for chapter in source_chapters]
        generated_beats: list[Beat] = []

        for offset, beat_data in enumerate(beats_data):
            if not isinstance(beat_data, dict):
                raise ValueError("beat_generator AI beat items must be dicts.")

            beat_id = str(
                beat_data.get("beat_id")
                or f"{self._generated_prefix(scene.scene_id)}{offset + 1:03d}"
            )
            if not beat_id.startswith(self._generated_prefix(scene.scene_id)):
                beat_id = f"{self._generated_prefix(scene.scene_id)}{offset + 1:03d}"

            generated_beats.append(
                Beat(
                    beat_id=beat_id,
                    scene_id=scene.scene_id,
                    order_index=starting_order_index + offset,
                    source_refs=source_refs,
                    story_function=str(beat_data.get("story_function", "")),
                    characters=[
                        str(value) for value in beat_data.get("characters", scene.characters)
                    ],
                    location=str(beat_data.get("location", scene.location)),
                    action=str(beat_data.get("action", "")),
                    emotion=str(beat_data.get("emotion", "")),
                    shot_type=str(beat_data.get("shot_type", "")),
                    visual_description=str(beat_data.get("visual_description", "")),
                    review_text="",
                    image_prompt="",
                    negative_prompt="",
                    continuity_tags=[str(value) for value in beat_data.get("continuity_tags", [])],
                    status="planned",
                )
            )

        return generated_beats

    def _ai_beats_data(self, response: dict[str, Any]) -> list[Any]:
        if not isinstance(response, dict):
            raise ValueError("beat_generator AI response must be a dict.")
        beats_data = response.get("beats", [])
        if not isinstance(beats_data, list) or not beats_data:
            raise ValueError("beat_generator AI response field 'beats' must be a non-empty list.")
        return beats_data

    def _beat_count_for_scene(self, scene: Scene, retelling_density: str) -> int:
        importance = scene.importance if scene.importance else "medium"
        importance_bonus = self._importance_bonus.get(importance, 1)

        if scene.target_beats > 0:
            count = round(scene.target_beats * self._target_multipliers[retelling_density])
            return max(2, count + importance_bonus)

        return self._base_beat_counts[retelling_density] + importance_bonus

    def _extract_scene_moments(self, scene: Scene) -> list[str]:
        candidates: list[str] = []
        for line in scene.summary.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            lowered = stripped.lower()
            if lowered.startswith("source:") or lowered.startswith("planning note:"):
                continue
            if lowered.startswith("important events to preserve:"):
                candidates.extend(self._split_preserved_events(stripped))
                continue
            candidates.extend(self._split_sentences(stripped))

        if not candidates:
            candidates = [scene.title]

        return [self._clean_moment(moment) for moment in candidates if moment.strip()]

    def _split_preserved_events(self, line: str) -> list[str]:
        _, _, value = line.partition(":")
        return [part.strip() for part in value.split("|") if part.strip()]

    def _split_sentences(self, text: str) -> list[str]:
        normalized = re.sub(r"\s+", " ", text.strip())
        sentences = re.split(r"(?<=[.!?。！？])\s+", normalized)
        return [sentence.strip() for sentence in sentences if sentence.strip()]

    def _clean_moment(self, moment: str) -> str:
        return moment.strip(" \t\r\n")

    def _story_function_for_index(self, beat_index: int, beat_count: int) -> str:
        if beat_index == 1:
            return "hook"
        if beat_index == beat_count:
            return "cliffhanger"
        return self._story_functions[(beat_index - 1) % (len(self._story_functions) - 1)]

    def _emotion_for_scene(self, scene: Scene, offset: int) -> str:
        lowered_mood = scene.mood.lower()
        for keyword, emotion in self._emotion_keywords.items():
            if keyword in lowered_mood:
                return emotion
        return self._default_emotions[offset % len(self._default_emotions)]

    def _build_action(self, story_function: str, moment: str) -> str:
        return f"{story_function}: focus on {moment}"

    def _build_visual_description(
        self,
        *,
        scene: Scene,
        moment: str,
        emotion: str,
        shot_type: str,
    ) -> str:
        character_text = ", ".join(scene.characters) if scene.characters else "the scene"
        location_text = scene.location or "the current location"
        return (
            f"{shot_type} of {character_text} at {location_text}, "
            f"showing {moment}, with a {emotion} mood."
        )

    def _build_continuity_tags(
        self,
        *,
        episode_id: str,
        scene: Scene,
        source_refs: list[str],
        retelling_density: str,
    ) -> list[str]:
        tags = [
            episode_id,
            scene.scene_id,
            f"density_{retelling_density}",
        ]
        tags.extend(source_refs)
        tags.extend(scene.characters)
        if scene.location:
            tags.append(scene.location)
        if scene.mood:
            tags.append(self._slug(scene.mood))
        return list(dict.fromkeys(tags))

    def _source_chapters_for_episode(
        self, project: Project, episode_id: str
    ) -> list[SourceChapter]:
        episode = self.project_service.find_episode(project, episode_id)
        chapters_by_id = {
            source_chapter.chapter_id: source_chapter for source_chapter in project.source_chapters
        }
        return [
            chapters_by_id[chapter_id]
            for chapter_id in episode.source_chapter_ids
            if chapter_id in chapters_by_id
        ]

    def _require_ai_gateway(self) -> AIGateway:
        if self.ai_gateway is None:
            raise ValueError("use_ai=True requires an ai_gateway.")
        return self.ai_gateway

    def _generated_prefix(self, scene_id: str) -> str:
        return f"beat_{scene_id}_"

    def _slug(self, value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")

    def _validate_density(self, retelling_density: str) -> None:
        if retelling_density not in self._allowed_retelling_densities:
            raise ValueError(f"Unsupported retelling_density: {retelling_density}")
