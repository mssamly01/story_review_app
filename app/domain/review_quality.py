"""Review narration quality result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ReviewQualityIssue:
    severity: str
    category: str
    message: str
    suggestion: str = ""
    beat_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "suggestion": self.suggestion,
            "beat_id": self.beat_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewQualityIssue":
        return cls(
            severity=data["severity"],
            category=data["category"],
            message=data["message"],
            suggestion=data.get("suggestion", ""),
            beat_id=data.get("beat_id", ""),
        )


@dataclass(slots=True)
class ReviewQualityResult:
    beat_id: str
    score: int
    grade: str
    is_ready: bool
    issues: list[ReviewQualityIssue] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "beat_id": self.beat_id,
            "score": self.score,
            "grade": self.grade,
            "is_ready": self.is_ready,
            "issues": [issue.to_dict() for issue in self.issues],
            "suggestions": list(self.suggestions),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewQualityResult":
        return cls(
            beat_id=data["beat_id"],
            score=int(data["score"]),
            grade=data["grade"],
            is_ready=bool(data["is_ready"]),
            issues=[ReviewQualityIssue.from_dict(issue) for issue in data.get("issues", [])],
            suggestions=list(data.get("suggestions", [])),
        )
