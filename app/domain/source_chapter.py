"""Original source chapter domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class SourceChapter:
    chapter_id: str
    title: str
    chapter_number: int
    raw_text: str
    notes: str = ""
    import_date: str = field(default_factory=_utc_now_iso)
    parsed_scene_ids: list[str] = field(default_factory=list)

    @property
    def word_count(self) -> int:
        return len(self.raw_text.split())

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_id": self.chapter_id,
            "title": self.title,
            "chapter_number": self.chapter_number,
            "raw_text": self.raw_text,
            "notes": self.notes,
            "import_date": self.import_date,
            "word_count": self.word_count,
            "parsed_scene_ids": list(self.parsed_scene_ids),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceChapter":
        return cls(
            chapter_id=data["chapter_id"],
            title=data["title"],
            chapter_number=int(data["chapter_number"]),
            raw_text=data.get("raw_text", ""),
            notes=data.get("notes", ""),
            import_date=data.get("import_date", _utc_now_iso()),
            parsed_scene_ids=list(data.get("parsed_scene_ids", [])),
        )
