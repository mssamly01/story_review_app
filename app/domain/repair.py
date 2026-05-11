"""Repair suggestion and result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RepairAction:
    action_id: str
    action_type: str
    severity: str
    title: str
    description: str
    target_entity_type: str = ""
    target_entity_id: str = ""
    episode_id: str = ""
    scene_id: str = ""
    beat_id: str = ""
    source_issue_ids: list[str] = field(default_factory=list)
    suggested_changes: dict[str, Any] = field(default_factory=dict)
    can_auto_apply: bool = False
    requires_user_review: bool = False
    risk_level: str = "low"

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "target_entity_type": self.target_entity_type,
            "target_entity_id": self.target_entity_id,
            "episode_id": self.episode_id,
            "scene_id": self.scene_id,
            "beat_id": self.beat_id,
            "source_issue_ids": list(self.source_issue_ids),
            "suggested_changes": dict(self.suggested_changes),
            "can_auto_apply": self.can_auto_apply,
            "requires_user_review": self.requires_user_review,
            "risk_level": self.risk_level,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RepairAction":
        return cls(
            action_id=data["action_id"],
            action_type=data["action_type"],
            severity=data["severity"],
            title=data["title"],
            description=data["description"],
            target_entity_type=data.get("target_entity_type", ""),
            target_entity_id=data.get("target_entity_id", ""),
            episode_id=data.get("episode_id", ""),
            scene_id=data.get("scene_id", ""),
            beat_id=data.get("beat_id", ""),
            source_issue_ids=list(data.get("source_issue_ids", [])),
            suggested_changes=dict(data.get("suggested_changes", {})),
            can_auto_apply=bool(data.get("can_auto_apply", False)),
            requires_user_review=bool(data.get("requires_user_review", False)),
            risk_level=data.get("risk_level", "low"),
        )


@dataclass(slots=True)
class RepairResult:
    action_id: str
    applied: bool
    message: str
    changed_entity_type: str = ""
    changed_entity_id: str = ""
    before_snapshot: dict[str, Any] | None = None
    after_snapshot: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "applied": self.applied,
            "message": self.message,
            "changed_entity_type": self.changed_entity_type,
            "changed_entity_id": self.changed_entity_id,
            "before_snapshot": self.before_snapshot,
            "after_snapshot": self.after_snapshot,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RepairResult":
        return cls(
            action_id=data["action_id"],
            applied=bool(data["applied"]),
            message=data["message"],
            changed_entity_type=data.get("changed_entity_type", ""),
            changed_entity_id=data.get("changed_entity_id", ""),
            before_snapshot=data.get("before_snapshot"),
            after_snapshot=data.get("after_snapshot"),
        )
