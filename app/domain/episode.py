"""Review episode domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domain.scene import Scene


@dataclass(slots=True)
class ReviewEpisode:
    episode_id: str
    title: str
    source_chapter_ids: list[str] = field(default_factory=list)
    tone: str = "mysterious"
    density: str = "full"
    scenes: list[Scene] = field(default_factory=list)
    status: str = "draft"
    summary: str = ""
    hook: str = ""
    cliffhanger: str = ""

    @property
    def scene_ids(self) -> list[str]:
        return [scene.scene_id for scene in self.scenes]

    @property
    def estimated_beats(self) -> int:
        return sum(len(scene.beats) if scene.beats else scene.target_beats for scene in self.scenes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "title": self.title,
            "source_chapter_ids": list(self.source_chapter_ids),
            "tone": self.tone,
            "density": self.density,
            "status": self.status,
            "summary": self.summary,
            "hook": self.hook,
            "cliffhanger": self.cliffhanger,
            "scene_ids": self.scene_ids,
            "estimated_beats": self.estimated_beats,
            "scenes": [scene.to_dict() for scene in self.scenes],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewEpisode":
        return cls(
            episode_id=data["episode_id"],
            title=data["title"],
            source_chapter_ids=list(data.get("source_chapter_ids", [])),
            tone=data.get("tone", "mysterious"),
            density=data.get("density", "full"),
            status=data.get("status", "draft"),
            summary=data.get("summary", ""),
            hook=data.get("hook", ""),
            cliffhanger=data.get("cliffhanger", ""),
            scenes=[Scene.from_dict(scene) for scene in data.get("scenes", [])],
        )
