"""Deterministic mock story parser.

This service prepares the SourceChapter -> parsed story structure pipeline
without calling AI. The output schema is intentionally JSON-like so a future
AI parser can return the same shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from app.domain.source_chapter import SourceChapter


@dataclass(slots=True)
class DetectedCharacter:
    name: str
    role: str = "unknown"
    evidence: str = ""
    confidence: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "evidence": self.evidence,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class DetectedLocation:
    name: str
    mood: str = "neutral"
    evidence: str = ""
    confidence: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "mood": self.mood,
            "evidence": self.evidence,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class ImportantEvent:
    event_id: str
    summary: str
    characters: list[str] = field(default_factory=list)
    location: str = ""
    evidence: str = ""
    importance: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "summary": self.summary,
            "characters": list(self.characters),
            "location": self.location,
            "evidence": self.evidence,
            "importance": self.importance,
        }


@dataclass(slots=True)
class SceneCandidate:
    scene_id: str
    title: str
    summary: str
    mood: str = "neutral"
    characters: list[str] = field(default_factory=list)
    location: str = ""
    important_events: list[str] = field(default_factory=list)
    importance: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "title": self.title,
            "summary": self.summary,
            "mood": self.mood,
            "characters": list(self.characters),
            "location": self.location,
            "important_events": list(self.important_events),
            "importance": self.importance,
        }


@dataclass(slots=True)
class ParsedChapterResult:
    chapter_id: str
    detected_characters: list[DetectedCharacter] = field(default_factory=list)
    detected_locations: list[DetectedLocation] = field(default_factory=list)
    scene_candidates: list[SceneCandidate] = field(default_factory=list)
    important_events: list[ImportantEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_id": self.chapter_id,
            "detected_characters": [
                character.to_dict() for character in self.detected_characters
            ],
            "detected_locations": [
                location.to_dict() for location in self.detected_locations
            ],
            "scene_candidates": [
                scene_candidate.to_dict()
                for scene_candidate in self.scene_candidates
            ],
            "important_events": [
                important_event.to_dict()
                for important_event in self.important_events
            ],
        }


class StoryParserService:
    _character_pattern = re.compile(
        r"\b[A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠƯẠ-Ỵ][^\W\d_]*"
        r"(?:\s+[A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠƯẠ-Ỵ][^\W\d_]*){1,3}",
        re.UNICODE,
    )
    _sentence_split_pattern = re.compile(r"(?<=[.!?。！？])\s+")
    _location_patterns = [
        re.compile(pattern, re.IGNORECASE | re.UNICODE)
        for pattern in [
            r"\b(căn nhà(?:\s+(?:cũ|hoang|bỏ hoang))?)",
            r"\b(ngôi nhà(?:\s+(?:cũ|hoang|bỏ hoang))?)",
            r"\b(căn phòng(?:\s+(?:bị khóa|khóa|cũ|bí mật))?)",
            r"\b(hành lang(?:\s+(?:phía sau|cuối|cũ|tối))?)",
            r"\b(khu rừng(?:\s+(?:cấm|tối|sâu))?)",
            r"\b(thành phố(?:\s+(?:cũ|ngầm|đổ nát))?)",
            r"\b(ngôi làng(?:\s+(?:cũ|bị bỏ hoang))?)",
            r"\b(trường học(?:\s+(?:cũ|bỏ hoang))?)",
            r"\b(bệnh viện(?:\s+(?:cũ|bỏ hoang))?)",
        ]
    ]
    _event_keywords = [
        "trở về",
        "bước vào",
        "phát hiện",
        "nhận ra",
        "nghe thấy",
        "nhìn thấy",
        "tìm thấy",
        "xuất hiện",
        "gặp",
        "mở",
        "khóa",
        "chạy",
        "tấn công",
    ]
    _mood_keywords = {
        "mysterious": ["bí ẩn", "kỳ lạ", "lạ", "khóa", "tiếng động"],
        "tense": ["sợ", "căng", "nguy hiểm", "tấn công", "run"],
        "lonely": ["một mình", "xa cách", "cô độc", "vắng"],
        "dramatic": ["máu", "bí mật", "bi kịch", "la hét"],
    }

    def parse(self, source_chapter: SourceChapter) -> ParsedChapterResult:
        text = source_chapter.raw_text
        sentences = self._split_sentences(text)
        characters = self._detect_characters(sentences)
        locations = self._detect_locations(sentences)
        important_events = self._detect_important_events(
            sentences=sentences,
            characters=characters,
            locations=locations,
        )
        scene_candidates = self._build_scene_candidates(
            source_chapter=source_chapter,
            characters=characters,
            locations=locations,
            important_events=important_events,
        )
        return ParsedChapterResult(
            chapter_id=source_chapter.chapter_id,
            detected_characters=characters,
            detected_locations=locations,
            scene_candidates=scene_candidates,
            important_events=important_events,
        )

    def _split_sentences(self, text: str) -> list[str]:
        normalized = re.sub(r"\s+", " ", text.strip())
        if not normalized:
            return []
        sentences = self._sentence_split_pattern.split(normalized)
        return [sentence.strip() for sentence in sentences if sentence.strip()]

    def _detect_characters(
        self, sentences: list[str]
    ) -> list[DetectedCharacter]:
        character_names: list[str] = []
        evidence_by_name: dict[str, str] = {}

        for sentence in sentences:
            for match in self._character_pattern.finditer(sentence):
                name = self._strip_phrase(match.group(0))
                if name not in character_names:
                    character_names.append(name)
                    evidence_by_name[name] = sentence

        return [
            DetectedCharacter(
                name=name,
                role="unknown",
                evidence=evidence_by_name[name],
                confidence=0.5,
            )
            for name in character_names
        ]

    def _detect_locations(self, sentences: list[str]) -> list[DetectedLocation]:
        location_names: list[str] = []
        evidence_by_name: dict[str, str] = {}
        mood_by_name: dict[str, str] = {}

        for sentence in sentences:
            for pattern in self._location_patterns:
                for match in pattern.finditer(sentence):
                    name = self._strip_phrase(match.group(1))
                    if name not in location_names:
                        location_names.append(name)
                        evidence_by_name[name] = sentence
                        mood_by_name[name] = self._detect_mood(sentence)

        return [
            DetectedLocation(
                name=name,
                mood=mood_by_name[name],
                evidence=evidence_by_name[name],
                confidence=0.5,
            )
            for name in location_names
        ]

    def _detect_important_events(
        self,
        *,
        sentences: list[str],
        characters: list[DetectedCharacter],
        locations: list[DetectedLocation],
    ) -> list[ImportantEvent]:
        events: list[ImportantEvent] = []
        for sentence in sentences:
            lowered_sentence = sentence.lower()
            if not any(keyword in lowered_sentence for keyword in self._event_keywords):
                continue

            event_id = f"ev_{len(events) + 1:03d}"
            events.append(
                ImportantEvent(
                    event_id=event_id,
                    summary=sentence,
                    characters=self._names_present(sentence, characters),
                    location=self._first_location_present(sentence, locations),
                    evidence=sentence,
                    importance="medium",
                )
            )

        return events

    def _build_scene_candidates(
        self,
        *,
        source_chapter: SourceChapter,
        characters: list[DetectedCharacter],
        locations: list[DetectedLocation],
        important_events: list[ImportantEvent],
    ) -> list[SceneCandidate]:
        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", source_chapter.raw_text)
            if paragraph.strip()
        ]
        if not paragraphs and source_chapter.raw_text.strip():
            paragraphs = [source_chapter.raw_text.strip()]

        scene_candidates: list[SceneCandidate] = []
        for index, paragraph in enumerate(paragraphs, start=1):
            scene_id = f"sc_{index:03d}"
            scene_event_ids = [
                event.event_id
                for event in important_events
                if event.evidence and event.evidence in paragraph
            ]
            scene_candidates.append(
                SceneCandidate(
                    scene_id=scene_id,
                    title=self._build_scene_title(index, paragraph),
                    summary=self._truncate(paragraph),
                    mood=self._detect_mood(paragraph),
                    characters=self._names_present(paragraph, characters),
                    location=self._first_location_present(paragraph, locations),
                    important_events=scene_event_ids,
                    importance="high" if scene_event_ids else "medium",
                )
            )

        return scene_candidates

    def _build_scene_title(self, index: int, paragraph: str) -> str:
        first_sentence = self._split_sentences(paragraph)[0]
        return f"Scene {index}: {self._truncate(first_sentence, limit=48)}"

    def _detect_mood(self, text: str) -> str:
        lowered_text = text.lower()
        for mood, keywords in self._mood_keywords.items():
            if any(keyword in lowered_text for keyword in keywords):
                return mood
        return "neutral"

    def _names_present(
        self, text: str, characters: list[DetectedCharacter]
    ) -> list[str]:
        return [character.name for character in characters if character.name in text]

    def _first_location_present(
        self, text: str, locations: list[DetectedLocation]
    ) -> str:
        for location in locations:
            if location.name in text:
                return location.name
        return ""

    def _strip_phrase(self, phrase: str) -> str:
        return phrase.strip(" \t\r\n.,;:!?()[]{}\"'")

    def _truncate(self, text: str, *, limit: int = 120) -> str:
        normalized = re.sub(r"\s+", " ", text.strip())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3].rstrip() + "..."
