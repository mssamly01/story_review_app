"""Production readiness report models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domain.validation import ValidationIssue

ProductionReadinessStatus = str


@dataclass(slots=True)
class ProductionReadinessReport:
    project_id: str
    project_title: str
    episode_id: str
    episode_title: str
    status: ProductionReadinessStatus
    overall_score: int
    validation_error_count: int
    validation_warning_count: int
    continuity_issue_count: int
    review_average_score: float
    prompt_average_score: float
    total_beats: int
    ready_review_beats: int
    ready_prompt_beats: int
    blocked_reasons: list[str] = field(default_factory=list)
    top_recommendations: list[str] = field(default_factory=list)
    validation_issues: list[ValidationIssue] = field(default_factory=list)
    continuity_issues: list[ValidationIssue] = field(default_factory=list)
    review_quality_summary: dict[str, Any] = field(default_factory=dict)
    prompt_quality_summary: dict[str, Any] = field(default_factory=dict)
    export_readiness: dict[str, Any] = field(default_factory=dict)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_title": self.project_title,
            "episode_id": self.episode_id,
            "episode_title": self.episode_title,
            "status": self.status,
            "overall_score": self.overall_score,
            "validation_error_count": self.validation_error_count,
            "validation_warning_count": self.validation_warning_count,
            "continuity_issue_count": self.continuity_issue_count,
            "review_average_score": self.review_average_score,
            "prompt_average_score": self.prompt_average_score,
            "total_beats": self.total_beats,
            "ready_review_beats": self.ready_review_beats,
            "ready_prompt_beats": self.ready_prompt_beats,
            "blocked_reasons": list(self.blocked_reasons),
            "top_recommendations": list(self.top_recommendations),
            "validation_issues": [issue.to_dict() for issue in self.validation_issues],
            "continuity_issues": [issue.to_dict() for issue in self.continuity_issues],
            "review_quality_summary": self.review_quality_summary,
            "prompt_quality_summary": self.prompt_quality_summary,
            "export_readiness": self.export_readiness,
            "generated_at": self.generated_at,
        }
