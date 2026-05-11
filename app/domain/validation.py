"""Structured validation issue model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ValidationIssue:
    issue_id: str
    severity: str
    category: str
    message: str
    suggestion: str = ""
    entity_type: str = ""
    entity_id: str = ""
    episode_id: str = ""
    scene_id: str = ""
    beat_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "suggestion": self.suggestion,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "episode_id": self.episode_id,
            "scene_id": self.scene_id,
            "beat_id": self.beat_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValidationIssue":
        return cls(
            issue_id=data["issue_id"],
            severity=data["severity"],
            category=data["category"],
            message=data["message"],
            suggestion=data.get("suggestion", ""),
            entity_type=data.get("entity_type", ""),
            entity_id=data.get("entity_id", ""),
            episode_id=data.get("episode_id", ""),
            scene_id=data.get("scene_id", ""),
            beat_id=data.get("beat_id", ""),
        )
