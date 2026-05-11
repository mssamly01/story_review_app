"""Deterministic AI gateway used by tests and local development."""

from __future__ import annotations

import copy
import json
from typing import Any, Callable

from app.infrastructure.ai_gateway import AIGateway


class MockAIGateway(AIGateway):
    SUPPORTED_PROMPTS = {
        "story_parser",
        "episode_planner",
        "beat_generator",
        "review_rewriter",
        "image_prompt_builder",
        "continuity_checker",
        "beat_package_generator",
    }

    def generate_text(
        self,
        prompt_name: str,
        input_data: dict[str, Any],
        system_message: str | None = None,
    ) -> str:
        return json.dumps(
            self.generate_json(prompt_name, input_data, system_message),
            ensure_ascii=False,
            sort_keys=True,
        )

    def generate_json(
        self,
        prompt_name: str,
        input_data: dict[str, Any],
        system_message: str | None = None,
    ) -> dict[str, Any]:
        builders: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "story_parser": self._story_parser_response,
            "episode_planner": self._episode_planner_response,
            "beat_generator": self._beat_generator_response,
            "review_rewriter": self._review_rewriter_response,
            "image_prompt_builder": self._image_prompt_builder_response,
            "continuity_checker": self._continuity_checker_response,
            "beat_package_generator": self._beat_package_generator_response,
        }

        if prompt_name not in builders:
            supported = ", ".join(sorted(self.SUPPORTED_PROMPTS))
            raise ValueError(
                f"Unsupported prompt_name '{prompt_name}'. " f"Supported prompt names: {supported}."
            )

        response = builders[prompt_name](input_data)
        return copy.deepcopy(response)

    def _story_parser_response(self, input_data: dict[str, Any]) -> dict[str, Any]:
        chapter_id = str(input_data.get("chapter_id", "ch_mock"))
        return {
            "chapter_id": chapter_id,
            "detected_characters": [
                {
                    "name": "Mock Protagonist",
                    "role": "protagonist",
                    "evidence": "deterministic mock evidence",
                }
            ],
            "detected_locations": [
                {
                    "name": "Mock Location",
                    "mood": "mysterious",
                }
            ],
            "important_objects": ["mock clue"],
            "scene_candidates": [
                {
                    "title": "Mock opening scene",
                    "summary": "A focused setup scene for later beat planning.",
                    "importance": "high",
                    "characters": ["Mock Protagonist"],
                    "location": "Mock Location",
                    "mood": "mysterious",
                }
            ],
            "important_events": ["The protagonist discovers a mock clue."],
            "continuity_notes": ["Preserve the mock clue across beats."],
        }

    def _episode_planner_response(self, input_data: dict[str, Any]) -> dict[str, Any]:
        source_chapter_ids = list(input_data.get("source_chapter_ids", ["ch_mock"]))
        return {
            "episode": {
                "episode_title": "Mock Review Episode",
                "episode_summary": ("A detailed retelling plan that preserves cause and effect."),
                "source_chapter_ids": source_chapter_ids,
                "tone": input_data.get("narration_style", "mysterious"),
                "density": input_data.get("retelling_density", "full"),
                "hook": "A strange clue pulls the story forward.",
            },
            "scenes": [
                {
                    "scene_id": "sc_mock_001",
                    "title": "Mock discovery",
                    "summary": "The lead character notices a clue and reacts.",
                    "mood": "tense",
                    "characters": ["mock_protagonist"],
                    "location": "mock_location",
                    "target_beats": 4,
                    "importance": "high",
                }
            ],
            "cliffhanger": "The clue points to a hidden room.",
        }

    def _beat_generator_response(self, input_data: dict[str, Any]) -> dict[str, Any]:
        scene_id = str(input_data.get("scene_id", "sc_mock_001"))
        return {
            "beats": [
                {
                    "beat_id": f"beat_{scene_id}_001",
                    "scene_id": scene_id,
                    "order_index": 1,
                    "story_function": "discovery",
                    "characters": ["mock_protagonist"],
                    "location": "mock_location",
                    "action": "finds a clue on the floor",
                    "emotion": "curious",
                    "shot_type": "detail shot",
                    "visual_description": "a small clue lying on a dusty floor",
                    "continuity_tags": [
                        scene_id,
                        "mock_protagonist",
                        "mock_location",
                    ],
                }
            ]
        }

    def _review_rewriter_response(self, input_data: dict[str, Any]) -> dict[str, Any]:
        beat_id = str(input_data.get("beat_id", "beat_mock_001"))
        return {
            "rewritten_beats": [
                {
                    "beat_id": beat_id,
                    "review_text": (
                        "Ngay luc nay, nhan vat chinh cham lai va nhan ra "
                        "mot chi tiet quan trong dang nam ngay truoc mat."
                    ),
                }
            ]
        }

    def _image_prompt_builder_response(self, input_data: dict[str, Any]) -> dict[str, Any]:
        beat_id = str(input_data.get("beat_id", "beat_mock_001"))
        return {
            "prompts": [
                {
                    "beat_id": beat_id,
                    "image_prompt": (
                        "cinematic webtoon style, mock protagonist finding a "
                        "small clue on a dusty floor, curious expression, "
                        "detail shot, high quality illustration"
                    ),
                    "negative_prompt": (
                        "low quality, blurry, distorted anatomy, extra fingers, "
                        "inconsistent face, wrong outfit, text, watermark, logo"
                    ),
                }
            ]
        }

    def _continuity_checker_response(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "issues": [],
            "checked_categories": [
                "character_appearance",
                "outfit",
                "location",
                "time_of_day",
                "object_state",
                "relationship_logic",
                "emotional_continuity",
            ],
        }

    def _beat_package_generator_response(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "beats": [
                {
                    "order_index": 1,
                    "story_function": "discovery",
                    "characters": ["mock_protagonist"],
                    "location": "mock_location",
                    "action": "finds a clue on the floor",
                    "emotion": "curious",
                    "shot_type": "detail shot",
                    "visual_description": "a small clue lying on a dusty floor",
                    "review_text": "Ngay lúc này, nhân vật chính chậm lại và nhận ra một chi tiết quan trọng.",
                    "image_prompt": "cinematic webtoon style, mock protagonist finding a small clue on a dusty floor, high quality",
                    "negative_prompt": "low quality, blurry, text, watermark, logo",
                    "continuity_tags": ["mock_protagonist", "mock_location"],
                },
                {
                    "order_index": 2,
                    "story_function": "reaction",
                    "characters": ["mock_protagonist"],
                    "location": "mock_location",
                    "action": "examines the clue closely",
                    "emotion": "surprised",
                    "shot_type": "close-up",
                    "visual_description": "close up of eyes reflecting the light from the clue",
                    "review_text": "Sự ngạc nhiên hiện rõ trên khuôn mặt khi sự thật bắt đầu hé lộ.",
                    "image_prompt": "cinematic webtoon style, close up of mock protagonist eyes reflecting light, high quality",
                    "negative_prompt": "low quality, blurry, text, watermark, logo",
                    "continuity_tags": ["mock_protagonist"],
                },
            ]
        }
