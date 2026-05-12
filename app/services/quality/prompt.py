"""Offline prompt quality scoring and preview reports."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from app.domain.beat import Beat
from app.domain.character import Character
from app.domain.episode import ReviewEpisode
from app.domain.location import Location
from app.domain.project import Project
from app.domain.prompt_quality import PromptQualityIssue, PromptQualityResult
from app.domain.scene import Scene
from app.domain.style_preset import StylePreset
from app.services.project_service import ProjectService


class PromptQualityService:
    REQUIRED_NEGATIVE_TERMS = [
        "low quality",
        "blurry",
        "text",
        "watermark",
        "logo",
        "speech bubble",
    ]
    TEXT_REQUEST_TERMS = [
        "text",
        "text overlay",
        "visible text",
        "written words",
        "subtitle",
        "subtitles",
        "caption",
        "captions",
    ]
    BRAND_REQUEST_TERMS = ["logo", "watermark"]
    SPEECH_REQUEST_TERMS = ["speech bubble", "speech bubbles"]
    SEQUENCE_TERMS = ["then", "after that", "next scene", "multiple scenes"]
    STYLE_FALLBACK_TERMS = ["style", "webtoon", "comic", "manhwa", "manhua", "illustration"]
    TERM_STOPWORDS = {
        "and",
        "are",
        "cinematic",
        "clear",
        "detailed",
        "high",
        "illustration",
        "quality",
        "single",
        "style",
        "the",
        "with",
    }

    def __init__(self, project_service: ProjectService | None = None) -> None:
        self.project_service = project_service or ProjectService()

    def score_beat_prompt(
        self,
        project: Project,
        beat_id: str,
    ) -> PromptQualityResult:
        episode, scene, beat = self._find_beat_context(project, beat_id)
        style_preset = self._selected_style_preset(project)
        score = 100
        issues: list[PromptQualityIssue] = []
        image_prompt = beat.image_prompt.strip()
        negative_prompt = beat.negative_prompt.strip()

        if not image_prompt:
            score -= self._add_issue(
                issues,
                beat.beat_id,
                severity="error",
                category="missing_prompt",
                message="Beat has no image prompt.",
                suggestion="Build an image prompt before sending this beat onward.",
                penalty=80,
            )
        else:
            score -= self._score_positive_prompt(
                project,
                episode,
                scene,
                beat,
                style_preset,
                image_prompt,
                issues,
            )

        score -= self._score_negative_prompt(
            project,
            scene,
            beat,
            style_preset,
            negative_prompt,
            issues,
        )

        score = max(0, min(100, score))
        grade = self._grade(score)
        is_ready = score >= 80 and not any(issue.severity == "error" for issue in issues)
        suggestions = list(dict.fromkeys(issue.suggestion for issue in issues if issue.suggestion))
        return PromptQualityResult(
            beat_id=beat.beat_id,
            score=score,
            grade=grade,
            is_ready=is_ready,
            issues=issues,
            suggestions=suggestions,
        )

    def score_scene_prompts(
        self,
        project: Project,
        scene_id: str,
    ) -> list[PromptQualityResult]:
        _episode, scene = self._find_scene_context(project, scene_id)
        return [self.score_beat_prompt(project, beat.beat_id) for beat in scene.ordered_beats()]

    def score_episode_prompts(
        self,
        project: Project,
        episode_id: str,
    ) -> list[PromptQualityResult]:
        episode = self.project_service.find_episode(project, episode_id)
        return [
            self.score_beat_prompt(project, beat.beat_id)
            for scene in episode.scenes
            for beat in scene.ordered_beats()
        ]

    def build_episode_report(
        self,
        project: Project,
        episode_id: str,
    ) -> dict[str, Any]:
        episode = self.project_service.find_episode(project, episode_id)
        results = self.score_episode_prompts(project, episode_id)
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

    def export_episode_report_markdown(
        self,
        project: Project,
        episode_id: str,
    ) -> str:
        report = self.build_episode_report(project, episode_id)
        lines = [
            f"# Prompt Quality Report - {report['episode_title']}",
            "",
            f"- Episode ID: `{report['episode_id']}`",
            f"- Average score: {report['average_score']}",
            f"- Ready: {report['ready_count']}",
            f"- Not ready: {report['not_ready_count']}",
            "",
            "## Grade Distribution",
            "",
        ]
        for grade in ["A", "B", "C", "D", "F"]:
            lines.append(f"- {grade}: {report['grade_distribution'].get(grade, 0)}")

        lines.extend(["", "## Common Issues", ""])
        if report["common_issues"]:
            for item in report["common_issues"]:
                lines.append(f"- {item['category']}: {item['count']}")
        else:
            lines.append("- None")

        lines.extend(
            [
                "",
                "## Beat Results",
                "",
                "| Beat ID | Score | Grade | Ready | Top Issues | Suggestions |",
                "|---|---:|:---:|:---:|---|---|",
            ]
        )
        for result in report["results"]:
            top_issues = ", ".join(issue["category"] for issue in result["issues"][:3]) or "None"
            suggestions = "; ".join(result["suggestions"][:2]) or "None"
            ready = "yes" if result["is_ready"] else "no"
            lines.append(
                f"| `{result['beat_id']}` | {result['score']} | "
                f"{result['grade']} | {ready} | {top_issues} | {suggestions} |"
            )

        return "\n".join(lines).rstrip() + "\n"

    def _score_positive_prompt(
        self,
        project: Project,
        episode: ReviewEpisode,
        scene: Scene,
        beat: Beat,
        style_preset: StylePreset | None,
        image_prompt: str,
        issues: list[PromptQualityIssue],
    ) -> int:
        penalty = 0
        prompt_length = len(image_prompt)
        if prompt_length < 80:
            penalty += self._add_issue(
                issues,
                beat.beat_id,
                severity="warning",
                category="too_short",
                message="Image prompt is very short.",
                suggestion="Add style, subject, location, action, emotion, and camera detail.",
                penalty=10,
            )
        if prompt_length > 900:
            penalty += self._add_issue(
                issues,
                beat.beat_id,
                severity="info",
                category="too_long",
                message="Image prompt is very long.",
                suggestion="Trim repeated details while keeping stable bible terms.",
                penalty=5,
            )

        penalty += self._score_style_terms(style_preset, image_prompt, beat.beat_id, issues)
        penalty += self._score_character_terms(project, beat, image_prompt, issues)
        penalty += self._score_location_terms(project, scene, beat, image_prompt, issues)
        penalty += self._score_story_terms(episode, scene, beat, image_prompt, issues)
        penalty += self._score_blocked_positive_terms(beat.beat_id, image_prompt, issues)
        return penalty

    def _score_style_terms(
        self,
        style_preset: StylePreset | None,
        image_prompt: str,
        beat_id: str,
        issues: list[PromptQualityIssue],
    ) -> int:
        if style_preset and style_preset.positive_prompt:
            if self._contains_visual_terms(image_prompt, style_preset.positive_prompt):
                return 0
        elif any(term in image_prompt.lower() for term in self.STYLE_FALLBACK_TERMS):
            return 0

        return self._add_issue(
            issues,
            beat_id,
            severity="warning",
            category="missing_style",
            message="Image prompt lacks clear style terms.",
            suggestion="Include the selected StylePreset positive prompt.",
            penalty=10,
        )

    def _score_character_terms(
        self,
        project: Project,
        beat: Beat,
        image_prompt: str,
        issues: list[PromptQualityIssue],
    ) -> int:
        penalty = 0
        for character_id in beat.characters:
            character = self._find_character(project, character_id)
            if character is None:
                penalty += self._add_issue(
                    issues,
                    beat.beat_id,
                    severity="warning",
                    category="inconsistent_character",
                    message=f"Referenced character {character_id} is not in the character bible.",
                    suggestion="Add the character bible entry or remove the reference.",
                    penalty=8,
                )
                continue
            if character.visual_prompt_base and not self._contains_visual_terms(
                image_prompt,
                character.visual_prompt_base,
            ):
                penalty += self._add_issue(
                    issues,
                    beat.beat_id,
                    severity="warning",
                    category="missing_character_detail",
                    message=f"Prompt omits key visual details for {character_id}.",
                    suggestion="Add Character.visual_prompt_base to the image prompt.",
                    penalty=12,
                )
            if (
                not character.visual_prompt_base
                and character.appearance
                and not self._contains_visual_terms(image_prompt, character.appearance)
            ):
                penalty += self._add_issue(
                    issues,
                    beat.beat_id,
                    severity="warning",
                    category="missing_character_detail",
                    message=f"Prompt omits appearance details for {character_id}.",
                    suggestion="Add the character appearance to the image prompt.",
                    penalty=10,
                )
            if character.default_outfit and not self._contains_visual_terms(
                image_prompt,
                character.default_outfit,
            ):
                penalty += self._add_issue(
                    issues,
                    beat.beat_id,
                    severity="warning",
                    category="missing_outfit",
                    message=f"Prompt omits default outfit for {character_id}.",
                    suggestion="Include the character default outfit for continuity.",
                    penalty=10,
                )

            # Resolve variant for visual checks
            variant_id = beat.character_variants.get(character_id)
            if not variant_id:
                variant_id = beat.character_variants.get(character.character_id, "")
            
            variant = character.find_variant(variant_id)
            if not variant and len(character.variants) == 1:
                variant = character.variants[0]
                
            source_obj = variant if variant else character

            # High Fidelity Checks
            for field_name in ["hair", "eyes", "body_type"]:
                val = getattr(source_obj, field_name, "")
                if val and not self._contains_visual_terms(image_prompt, val):
                    penalty += self._add_issue(
                        issues,
                        beat.beat_id,
                        severity="info",
                        category="missing_character_detail",
                        message=f"Prompt omits {field_name} for {character_id}.",
                        suggestion=f"Add character {field_name} details for better consistency.",
                        penalty=4,
                    )

            # Full block structure check
            # Pattern: Name followed by open parenthesis, some content, and close parenthesis
            # We use character.name because IDs shouldn't be in the prompt.
            block_pattern = rf"{re.escape(character.name)}[^(]*\([^)]+\)"
            if not re.search(block_pattern, image_prompt, re.IGNORECASE | re.DOTALL):
                penalty += self._add_issue(
                    issues,
                    beat.beat_id,
                    severity="warning",
                    category="missing_character_block",
                    message=f"Prompt lacks a full structured block for character: {character.name}.",
                    suggestion=f"Every character must have a detailed block like: {character.name} (Gender: ..., Age: ..., Outfit: ...)",
                    penalty=15,
                )
        return penalty

    def _score_location_terms(
        self,
        project: Project,
        scene: Scene,
        beat: Beat,
        image_prompt: str,
        issues: list[PromptQualityIssue],
    ) -> int:
        location_id = beat.location or scene.location
        if not location_id:
            return 0

        location = self._find_location(project, location_id)
        if location is None:
            return self._add_issue(
                issues,
                beat.beat_id,
                severity="warning",
                category="inconsistent_location",
                message=f"Referenced location {location_id} is not in the location bible.",
                suggestion="Add the location bible entry or remove the reference.",
                penalty=8,
            )

        penalty = 0
        if location.visual_prompt_base and not self._contains_visual_terms(
            image_prompt,
            location.visual_prompt_base,
        ):
            penalty += self._add_issue(
                issues,
                beat.beat_id,
                severity="warning",
                category="missing_location_detail",
                message=f"Prompt omits key visual details for {location_id}.",
                suggestion="Add Location.visual_prompt_base to the image prompt.",
                penalty=12,
            )
        if location.lighting and not self._contains_visual_terms(
            image_prompt,
            location.lighting,
        ):
            penalty += self._add_issue(
                issues,
                beat.beat_id,
                severity="warning",
                category="missing_lighting",
                message=f"Prompt omits lighting for {location_id}.",
                suggestion="Include the location lighting in the image prompt.",
                penalty=6,
            )
        if location.mood and not self._contains_visual_terms(image_prompt, location.mood):
            penalty += self._add_issue(
                issues,
                beat.beat_id,
                severity="info",
                category="missing_location_detail",
                message=f"Prompt omits mood for {location_id}.",
                suggestion="Add the location mood if it matters visually.",
                penalty=4,
            )

        # High Fidelity Checks
        for field_name in ["architecture_style", "recurring_props"]:
            val = getattr(location, field_name, "")
            if isinstance(val, list):
                val = ", ".join(val)
            if val and not self._contains_visual_terms(image_prompt, val):
                penalty += self._add_issue(
                    issues,
                    beat.beat_id,
                    severity="info",
                    category="missing_location_detail",
                    message=f"Prompt omits {field_name.replace('_', ' ')} for {location_id}.",
                    suggestion=f"Include {field_name.replace('_', ' ')} for a richer environment.",
                    penalty=3,
                )
        return penalty

    def _score_story_terms(
        self,
        episode: ReviewEpisode,
        scene: Scene,
        beat: Beat,
        image_prompt: str,
        issues: list[PromptQualityIssue],
    ) -> int:
        del episode
        penalty = 0
        if not beat.action and not beat.visual_description:
            penalty += self._add_issue(
                issues,
                beat.beat_id,
                severity="warning",
                category="missing_action",
                message="Beat lacks action and visual description.",
                suggestion="Add one clear visual moment for this beat.",
                penalty=12,
            )
        elif not (
            self._contains_visual_terms(image_prompt, beat.action)
            or self._contains_visual_terms(image_prompt, beat.visual_description)
        ):
            penalty += self._add_issue(
                issues,
                beat.beat_id,
                severity="warning",
                category="missing_action",
                message="Prompt does not reflect the beat action or visual focus.",
                suggestion="Include Beat.action or Beat.visual_description.",
                penalty=8,
            )

        if beat.emotion and not self._contains_visual_terms(image_prompt, beat.emotion):
            penalty += self._add_issue(
                issues,
                beat.beat_id,
                severity="warning",
                category="missing_emotion",
                message="Prompt omits beat emotion.",
                suggestion="Add the beat emotion as a visual mood or expression.",
                penalty=5,
            )

        shot_source = beat.shot_type or ""
        if shot_source and not self._contains_visual_terms(image_prompt, shot_source):
            penalty += self._add_issue(
                issues,
                beat.beat_id,
                severity="warning",
                category="missing_camera_shot",
                message="Prompt omits shot type or camera framing.",
                suggestion="Include Beat.shot_type in the prompt.",
                penalty=6,
            )

        lowered = image_prompt.lower()
        if any(term in lowered for term in self.SEQUENCE_TERMS):
            penalty += self._add_issue(
                issues,
                beat.beat_id,
                severity="warning",
                category="vague_visual_moment",
                message="Prompt appears to describe more than one moment.",
                suggestion="Rewrite it as one clear beat image.",
                penalty=10,
            )

        subject_markers = len(re.findall(r"\b(and|with|beside|behind)\b", lowered))
        if subject_markers > 12:
            penalty += self._add_issue(
                issues,
                beat.beat_id,
                severity="info",
                category="too_many_subjects",
                message="Prompt may contain too many subjects or competing details.",
                suggestion="Keep the beat focused on the main subject and action.",
                penalty=4,
            )
        if scene.mood and scene.mood.lower() not in lowered and not beat.emotion:
            penalty += self._add_issue(
                issues,
                beat.beat_id,
                severity="info",
                category="missing_emotion",
                message="Prompt omits scene mood.",
                suggestion="Add scene mood when beat emotion is empty.",
                penalty=3,
            )
        return penalty

    def _score_blocked_positive_terms(
        self,
        beat_id: str,
        image_prompt: str,
        issues: list[PromptQualityIssue],
    ) -> int:
        lowered = image_prompt.lower()
        penalty = 0
        text_terms = [
            term for term in self.TEXT_REQUEST_TERMS if self._contains_term(lowered, term)
        ]
        if text_terms:
            penalty += self._add_issue(
                issues,
                beat_id,
                severity="error",
                category="asks_for_text",
                message="Image prompt asks for visible text or captions.",
                suggestion="Move those terms to the negative prompt unless explicitly needed.",
                penalty=25,
            )
        brand_terms = [
            term for term in self.BRAND_REQUEST_TERMS if self._contains_term(lowered, term)
        ]
        if brand_terms:
            penalty += self._add_issue(
                issues,
                beat_id,
                severity="error",
                category="asks_for_logo_or_watermark",
                message="Image prompt asks for a logo or watermark.",
                suggestion="Remove branding requests from the image prompt.",
                penalty=25,
            )
        if any(term in lowered for term in self.SPEECH_REQUEST_TERMS):
            penalty += self._add_issue(
                issues,
                beat_id,
                severity="error",
                category="asks_for_text",
                message="Image prompt asks for speech bubbles.",
                suggestion="Keep dialogue out of the image prompt.",
                penalty=20,
            )
        return penalty

    def _score_negative_prompt(
        self,
        project: Project,
        scene: Scene,
        beat: Beat,
        style_preset: StylePreset | None,
        negative_prompt: str,
        issues: list[PromptQualityIssue],
    ) -> int:
        del project, scene, style_preset
        if not negative_prompt:
            return self._add_issue(
                issues,
                beat.beat_id,
                severity="warning",
                category="weak_negative_prompt",
                message="Beat has no negative prompt.",
                suggestion="Add common quality and no-text negative terms.",
                penalty=18,
            )

        missing_terms = [
            term for term in self.REQUIRED_NEGATIVE_TERMS if term not in negative_prompt.lower()
        ]
        if missing_terms:
            return self._add_issue(
                issues,
                beat.beat_id,
                severity="warning",
                category="weak_negative_prompt",
                message="Negative prompt is missing common guard terms.",
                suggestion="Add: " + ", ".join(missing_terms),
                penalty=min(15, len(missing_terms) * 3),
            )
        return 0

    def _add_issue(
        self,
        issues: list[PromptQualityIssue],
        beat_id: str,
        *,
        severity: str,
        category: str,
        message: str,
        suggestion: str,
        penalty: int,
    ) -> int:
        issues.append(
            PromptQualityIssue(
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

    def _contains_visual_terms(self, prompt: str, source: Any) -> bool:
        if not source:
            return False
        
        # Robustness: handle lists if they somehow leaked in
        if isinstance(source, list):
            source = ", ".join(str(i) for i in source)
        else:
            source = str(source)

        prompt_text = prompt.lower()
        terms = self._meaningful_terms(source)
        if not terms:
            return False
        matches = sum(1 for term in terms if term in prompt_text)
        return matches >= min(2, len(terms))

    def _meaningful_terms(self, value: Any) -> list[str]:
        # Robustness: Ensure value is a string before lower() and regex
        if isinstance(value, list):
            value = ", ".join(str(i) for i in value)
        else:
            value = str(value)

        words = re.findall(r"[a-zA-Z0-9]+", value.lower())
        terms: list[str] = []
        for word in words:
            if len(word) < 4 or word in self.TERM_STOPWORDS:
                continue
            if word not in terms:
                terms.append(word)
            if len(terms) >= 8:
                break
        return terms

    def _contains_term(self, lowered_prompt: str, term: str) -> bool:
        if " " in term:
            return term in lowered_prompt
        return re.search(rf"\b{re.escape(term)}\b", lowered_prompt) is not None

    def _selected_style_preset(self, project: Project) -> StylePreset | None:
        if not project.style_presets:
            return None
        preferred = self._slug(project.default_art_style)
        for style in project.style_presets:
            if self._slug(style.style_id) == preferred:
                return style
            if self._slug(style.name) == preferred:
                return style
        return project.style_presets[0]

    def _find_character(self, project: Project, character_id: str) -> Character | None:
        for character in project.characters:
            if character.character_id == character_id or character.name == character_id:
                return character
        return None

    def _find_location(self, project: Project, location_id: str) -> Location | None:
        for location in project.locations:
            if location.location_id == location_id or location.name == location_id:
                return location
        return None

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

    def _slug(self, value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
