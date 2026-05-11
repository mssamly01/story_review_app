"""Project aggregate root."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.domain.character import Character
from app.domain.episode import ReviewEpisode
from app.domain.location import Location
from app.domain.source_chapter import SourceChapter
from app.domain.style_preset import StylePreset


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


SCHEMA_VERSION = 2
"""Current project JSON schema version.

History:
- v1 (implicit, legacy): no ``schema_version`` field. Equivalent to v2 in
  structure; readers must migrate by stamping ``schema_version = 2``.
- v2: explicit ``schema_version`` field on every persisted project.
"""


@dataclass(slots=True)
class Project:
    project_id: str
    title: str
    author_source_note: str = ""
    genre: str = ""
    language: str = "vi"
    default_narration_style: str = "mysterious"
    default_art_style: str = "dark fantasy webtoon"
    retelling_density: str = "full"
    source_chapters: list[SourceChapter] = field(default_factory=list)
    review_episodes: list[ReviewEpisode] = field(default_factory=list)
    characters: list[Character] = field(default_factory=list)
    locations: list[Location] = field(default_factory=list)
    style_presets: list[StylePreset] = field(default_factory=list)
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)
    schema_version: int = SCHEMA_VERSION

    def touch(self) -> None:
        self.updated_at = _utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "title": self.title,
            "author_source_note": self.author_source_note,
            "genre": self.genre,
            "language": self.language,
            "default_narration_style": self.default_narration_style,
            "default_art_style": self.default_art_style,
            "retelling_density": self.retelling_density,
            "source_chapters": [chapter.to_dict() for chapter in self.source_chapters],
            "review_episodes": [episode.to_dict() for episode in self.review_episodes],
            "characters": [character.to_dict() for character in self.characters],
            "locations": [location.to_dict() for location in self.locations],
            "style_presets": [style_preset.to_dict() for style_preset in self.style_presets],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Project":
        return cls(
            project_id=data["project_id"],
            title=data["title"],
            author_source_note=data.get("author_source_note", ""),
            genre=data.get("genre", ""),
            language=data.get("language", "vi"),
            default_narration_style=data.get("default_narration_style", "mysterious"),
            default_art_style=data.get("default_art_style", "dark fantasy webtoon"),
            retelling_density=data.get("retelling_density", "full"),
            source_chapters=[
                SourceChapter.from_dict(chapter) for chapter in data.get("source_chapters", [])
            ],
            review_episodes=[
                ReviewEpisode.from_dict(episode) for episode in data.get("review_episodes", [])
            ],
            characters=[Character.from_dict(character) for character in data.get("characters", [])],
            locations=[Location.from_dict(location) for location in data.get("locations", [])],
            style_presets=[
                StylePreset.from_dict(style_preset)
                for style_preset in data.get("style_presets", [])
            ],
            created_at=data.get("created_at", _utc_now_iso()),
            updated_at=data.get("updated_at", _utc_now_iso()),
            schema_version=int(data.get("schema_version", 1)),
        )
