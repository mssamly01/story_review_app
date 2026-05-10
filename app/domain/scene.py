"""Scene domain model containing ordered beats."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domain.beat import Beat


@dataclass(slots=True)
class Scene:
    scene_id: str
    episode_id: str
    title: str
    summary: str = ""
    characters: list[str] = field(default_factory=list)
    location: str = ""
    mood: str = ""
    importance: str = "medium"
    target_beats: int = 0
    beats: list[Beat] = field(default_factory=list)

    @property
    def beat_ids(self) -> list[str]:
        return [beat.beat_id for beat in self.ordered_beats()]

    def ordered_beats(self) -> list[Beat]:
        return sorted(self.beats, key=lambda beat: beat.order_index)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "episode_id": self.episode_id,
            "title": self.title,
            "summary": self.summary,
            "characters": list(self.characters),
            "location": self.location,
            "mood": self.mood,
            "importance": self.importance,
            "target_beats": self.target_beats,
            "beat_ids": self.beat_ids,
            "beats": [beat.to_dict() for beat in self.ordered_beats()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Scene":
        return cls(
            scene_id=data["scene_id"],
            episode_id=data["episode_id"],
            title=data["title"],
            summary=data.get("summary", ""),
            characters=list(data.get("characters", [])),
            location=data.get("location", ""),
            mood=data.get("mood", ""),
            importance=data.get("importance", "medium"),
            target_beats=int(data.get("target_beats", 0)),
            beats=[Beat.from_dict(beat) for beat in data.get("beats", [])],
        )
