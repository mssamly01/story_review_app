"""Offline review narration quality scoring."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from app.domain.beat import Beat
from app.domain.episode import ReviewEpisode
from app.domain.project import Project
from app.domain.review_quality import ReviewQualityIssue, ReviewQualityResult
from app.domain.scene import Scene
from app.services.project_service import ProjectService


class ReviewQualityService:
    GENERIC_SUMMARY_TERMS = [
        "many things happen",
        "something happens",
        "short summary",
        "brief summary",
        "in summary",
    ]
    TERM_STOPWORDS = {
        "and",
        "are",
        "been",
        "into",
        "that",
        "the",
        "then",
        "this",
        "with",
        "when",
    }

    def __init__(self, project_service: ProjectService | None = None) -> None:
        self.project_service = project_service or ProjectService()

    def score_beat_review(
        self,
        project: Project,
        beat_id: str,
    ) -> ReviewQualityResult:
        _episode, scene, beat = self._find_beat_context(project, beat_id)
        score = 100
        issues: list[ReviewQualityIssue] = []
        review_text = beat.review_text.strip()

        if not review_text:
            score -= self._add_issue(
                issues,
                beat.beat_id,
                severity="error",
                category="missing_review_text",
                message="Beat has no review narration.",
                suggestion="Run rewrite-review for missing beats.",
                penalty=90,
            )
        else:
            score -= self._score_text_length(beat, review_text, issues)
            score -= self._score_beat_context(scene, beat, review_text, issues)
            score -= self._score_generic_text(beat, review_text, issues)
            score -= self._score_voiceover_shape(beat, review_text, issues)

        score = max(0, min(100, score))
        grade = self._grade(score)
        is_ready = score >= 80 and not any(issue.severity == "error" for issue in issues)
        suggestions = list(dict.fromkeys(issue.suggestion for issue in issues if issue.suggestion))
        return ReviewQualityResult(
            beat_id=beat.beat_id,
            score=score,
            grade=grade,
            is_ready=is_ready,
            issues=issues,
            suggestions=suggestions,
        )

    def score_scene_reviews(
        self,
        project: Project,
        scene_id: str,
    ) -> list[ReviewQualityResult]:
        _episode, scene = self._find_scene_context(project, scene_id)
        return [self.score_beat_review(project, beat.beat_id) for beat in scene.ordered_beats()]

    def score_episode_reviews(
        self,
        project: Project,
        episode_id: str,
    ) -> list[ReviewQualityResult]:
        episode = self.project_service.find_episode(project, episode_id)
        return [
            self.score_beat_review(project, beat.beat_id)
            for scene in episode.scenes
            for beat in scene.ordered_beats()
        ]

    def build_episode_report(
        self,
        project: Project,
        episode_id: str,
    ) -> dict[str, Any]:
        episode = self.project_service.find_episode(project, episode_id)
        results = self.score_episode_reviews(project, episode_id)
        total_beats = len(results)
        average_score = (
            round(sum(result.score for result in results) / total_beats, 2) if total_beats else 0.0
        )
        grade_distribution = dict(Counter(result.grade for result in results))
        ready_count = sum(1 for result in results if result.is_ready)
        issue_counter = Counter(issue.category for result in results for issue in result.issues)
        worst_beats = [
            result.to_dict() for result in sorted(results, key=lambda result: result.score)[:5]
        ]

        return {
            "episode_id": episode.episode_id,
            "episode_title": episode.title,
            "total_beats": total_beats,
            "average_score": average_score,
            "ready_count": ready_count,
            "not_ready_count": total_beats - ready_count,
            "grade_distribution": grade_distribution,
            "worst_beats": worst_beats,
            "common_issues": [
                {"category": category, "count": count}
                for category, count in issue_counter.most_common()
            ],
            "results": [result.to_dict() for result in results],
        }

    def _score_text_length(
        self,
        beat: Beat,
        review_text: str,
        issues: list[ReviewQualityIssue],
    ) -> int:
        words = re.findall(r"\w+", review_text, flags=re.UNICODE)
        if len(words) < 8:
            return self._add_issue(
                issues,
                beat.beat_id,
                severity="warning",
                category="too_short",
                message="Review narration is too short for a detailed retelling.",
                suggestion="Improve review narration for low-scoring beats.",
                penalty=45,
            )
        if len(words) < 22:
            return self._add_issue(
                issues,
                beat.beat_id,
                severity="warning",
                category="too_short",
                message="Review narration is short and may feel like a summary.",
                suggestion="Expand the beat with action, emotion, and scene context.",
                penalty=20,
            )
        if len(words) > 180:
            return self._add_issue(
                issues,
                beat.beat_id,
                severity="info",
                category="too_long",
                message="Review narration may be too long for one beat.",
                suggestion="Split the narration or trim repeated details.",
                penalty=5,
            )
        return 0

    def _score_beat_context(
        self,
        scene: Scene,
        beat: Beat,
        review_text: str,
        issues: list[ReviewQualityIssue],
    ) -> int:
        penalty = 0
        if beat.action and not self._contains_terms(review_text, beat.action):
            penalty += self._add_issue(
                issues,
                beat.beat_id,
                severity="warning",
                category="missing_action",
                message="Review narration does not clearly reflect the beat action.",
                suggestion="Include the beat action in the narration.",
                penalty=8,
            )
        if beat.emotion and not self._contains_terms(review_text, beat.emotion):
            penalty += self._add_issue(
                issues,
                beat.beat_id,
                severity="info",
                category="missing_emotion",
                message="Review narration does not reflect the beat emotion.",
                suggestion="Add emotional framing for the listener.",
                penalty=5,
            )
        if scene.mood and not self._contains_terms(review_text, scene.mood):
            penalty += self._add_issue(
                issues,
                beat.beat_id,
                severity="info",
                category="missing_scene_mood",
                message="Review narration omits the scene mood.",
                suggestion="Use scene mood to keep the retelling atmosphere clear.",
                penalty=4,
            )
        if scene.location and not self._contains_terms(review_text, scene.location):
            penalty += self._add_issue(
                issues,
                beat.beat_id,
                severity="info",
                category="missing_location_context",
                message="Review narration omits the scene location.",
                suggestion="Mention the setting when it affects the beat.",
                penalty=4,
            )
        return penalty

    def _score_generic_text(
        self,
        beat: Beat,
        review_text: str,
        issues: list[ReviewQualityIssue],
    ) -> int:
        lowered = review_text.lower()
        if any(term in lowered for term in self.GENERIC_SUMMARY_TERMS):
            return self._add_issue(
                issues,
                beat.beat_id,
                severity="warning",
                category="generic_summary",
                message="Review narration sounds like a generic summary.",
                suggestion="Retell the beat as a concrete story moment.",
                penalty=25,
            )
        return 0

    def _score_voiceover_shape(
        self,
        beat: Beat,
        review_text: str,
        issues: list[ReviewQualityIssue],
    ) -> int:
        sentence_count = len(re.findall(r"[.!?]+", review_text)) or 1
        if sentence_count == 1 and len(review_text) > 180:
            return self._add_issue(
                issues,
                beat.beat_id,
                severity="info",
                category="voiceover_pacing",
                message="Review narration is one long sentence.",
                suggestion="Break it into voice-over friendly sentences.",
                penalty=5,
            )
        return 0

    def _add_issue(
        self,
        issues: list[ReviewQualityIssue],
        beat_id: str,
        *,
        severity: str,
        category: str,
        message: str,
        suggestion: str,
        penalty: int,
    ) -> int:
        issues.append(
            ReviewQualityIssue(
                severity=severity,
                category=category,
                message=message,
                suggestion=suggestion,
                beat_id=beat_id,
            )
        )
        return penalty

    def _grade(self, score: int) -> str:
        if score >= 90:
            return "A"
        if score >= 80:
            return "B"
        if score >= 70:
            return "C"
        if score >= 60:
            return "D"
        return "F"

    def _contains_terms(self, text: str, source: str) -> bool:
        terms = self._meaningful_terms(source)
        if not terms:
            return True
        lowered = text.lower()
        matches = sum(1 for term in terms if term in lowered)
        return matches >= min(2, len(terms))

    def _meaningful_terms(self, value: str) -> list[str]:
        words = re.findall(r"[a-zA-Z0-9]+", value.lower())
        terms: list[str] = []
        for word in words:
            if len(word) < 4 or word in self.TERM_STOPWORDS:
                continue
            if word not in terms:
                terms.append(word)
            if len(terms) >= 6:
                break
        return terms

    def _find_beat_context(
        self,
        project: Project,
        beat_id: str,
    ) -> tuple[ReviewEpisode, Scene, Beat]:
        for episode in project.review_episodes:
            for scene in episode.scenes:
                for beat in scene.beats:
                    if beat.beat_id == beat_id:
                        return episode, scene, beat
        raise LookupError(f"Beat not found: {beat_id}")

    def _find_scene_context(
        self,
        project: Project,
        scene_id: str,
    ) -> tuple[ReviewEpisode, Scene]:
        for episode in project.review_episodes:
            for scene in episode.scenes:
                if scene.scene_id == scene_id:
                    return episode, scene
        raise LookupError(f"Scene not found: {scene_id}")
