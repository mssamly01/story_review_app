"""Unified beat package generation service.

This service generates story beats, review narration, and image prompts in a 
single unified workflow (one AI call or chained local services).
"""

from __future__ import annotations

import re
from typing import Any

from app.domain.beat import Beat
from app.domain.project import Project
from app.domain.scene import Scene
from app.domain.episode import ReviewEpisode
from app.infrastructure.ai_gateway import AIGateway
from app.services.project_service import ProjectService
from app.services.beat_generator_service import BeatGeneratorService
from app.services.review_rewriter_service import ReviewRewriterService
from app.services.prompt_builder_service import PromptBuilderService


class BeatPackageGeneratorService:
    def __init__(
        self,
        project_service: ProjectService | None = None,
        ai_gateway: AIGateway | None = None,
        beat_generator: BeatGeneratorService | None = None,
        review_rewriter: ReviewRewriterService | None = None,
        prompt_builder: PromptBuilderService | None = None,
    ) -> None:
        self.project_service = project_service or ProjectService()
        self.ai_gateway = ai_gateway
        self.beat_generator = beat_generator or BeatGeneratorService(
            project_service=self.project_service,
            ai_gateway=self.ai_gateway,
            use_ai=False
        )
        self.review_rewriter = review_rewriter or ReviewRewriterService(
            ai_gateway=self.ai_gateway,
            use_ai=False
        )
        self.prompt_builder = prompt_builder or PromptBuilderService(
            ai_gateway=self.ai_gateway,
            use_ai=False
        )

    def generate_for_scene(
        self,
        project: Project,
        episode_id: str,
        scene_id: str,
        narration_style: str | None = None,
        retelling_density: str | None = None,
        style_preset_id: str | None = None,
        use_ai: bool = False,
    ) -> list[Beat]:
        episode, scene = self._find_scene_context(project, episode_id, scene_id)
        
        if use_ai:
            return self._generate_with_ai(
                project=project,
                episode=episode,
                scene=scene,
                narration_style=narration_style,
                retelling_density=retelling_density,
                style_preset_id=style_preset_id,
            )
        else:
            return self._generate_deterministic(
                project=project,
                episode_id=episode_id,
                scene_id=scene_id,
                narration_style=narration_style,
                retelling_density=retelling_density,
                style_preset_id=style_preset_id,
            )

    def generate_for_episode(
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
                self.generate_for_scene(
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

    def _generate_deterministic(
        self,
        project: Project,
        episode_id: str,
        scene_id: str,
        narration_style: str | None = None,
        retelling_density: str | None = None,
        style_preset_id: str | None = None,
    ) -> list[Beat]:
        # 1. Generate Beats
        self.beat_generator.generate_beats_for_scene(
            project, episode_id, scene_id, retelling_density
        )
        
        # 2. Rewrite Review
        self.review_rewriter.rewrite_scene(
            project, scene_id, narration_style, retelling_density
        )
        
        # 3. Build Prompts
        self.prompt_builder.build_prompts_for_scene(
            project, scene_id, style_preset_id
        )
        
        episode, scene = self._find_scene_context(project, episode_id, scene_id)
        return scene.beats

    def _generate_with_ai(
        self,
        project: Project,
        episode: ReviewEpisode,
        scene: Scene,
        narration_style: str | None,
        retelling_density: str | None,
        style_preset_id: str | None,
    ) -> list[Beat]:
        gateway = self._require_ai_gateway()
        
        style_preset = self._find_style_preset(project, style_preset_id or project.default_art_style)
        source_chapters = self._source_chapters_for_episode(project, episode)
        
        input_data = {
            "project_genre": project.genre,
            "style_preset_name": style_preset.name if style_preset else "Default",
            "style_positive": style_preset.positive_prompt if style_preset else "",
            "style_negative": style_preset.negative_prompt if style_preset else "",
            "narration_style": narration_style or episode.tone,
            "retelling_density": retelling_density or episode.density,
            "character_bible": [c.to_dict() for c in project.characters],
            "location_bible": [l.to_dict() for l in project.locations],
            "episode_title": episode.title,
            "episode_summary": episode.summary,
            "scene_title": scene.title,
            "scene_summary": scene.summary,
            "source_text": "\n".join([c.raw_text for c in source_chapters]),
        }
        
        response = gateway.generate_json("beat_package_generator", input_data)
        beats_data = response.get("beats", [])
        
        # Preserve manually edited beats (optional, following existing patterns)
        preserved_beats = [
            beat for beat in scene.beats 
            if not beat.beat_id.startswith(f"beat_{scene.scene_id}_")
        ]
        
        new_beats: list[Beat] = []
        for i, b_data in enumerate(beats_data):
            beat_id = f"beat_{scene.scene_id}_{i+1:03d}"
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
                    status="planned"
                )
            )
        
        scene.beats = preserved_beats + new_beats
        project.touch()
        return new_beats

    def _find_scene_context(
        self, project: Project, episode_id: str, scene_id: str
    ) -> tuple[ReviewEpisode, Scene]:
        episode = self.project_service.find_episode(project, episode_id)
        for scene in episode.scenes:
            if scene.scene_id == scene_id:
                return episode, scene
        raise LookupError(f"Scene not found: {scene_id}")

    def _find_style_preset(self, project: Project, style_id: str) -> Any | None:
        for s in project.style_presets:
            if s.style_id == style_id or s.name == style_id:
                return s
        return None

    def _source_chapters_for_episode(self, project: Project, episode: ReviewEpisode) -> list[Any]:
        chapters_by_id = {c.chapter_id: c for c in project.source_chapters}
        return [
            chapters_by_id[cid] for cid in episode.source_chapter_ids if cid in chapters_by_id
        ]

    def _require_ai_gateway(self) -> AIGateway:
        if self.ai_gateway is None:
            raise ValueError("use_ai=True requires an ai_gateway.")
        return self.ai_gateway
