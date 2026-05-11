"""Tests for ManualAIService."""

from __future__ import annotations

import pytest

from app.services.manual_ai_service import SUPPORTED_STEPS, ManualAIService
from app.services.project_service import ProjectService


@pytest.fixture
def project_with_chapter():
    """Tạo project có sẵn 1 chapter để test."""
    service = ProjectService()
    project = service.create_project("Test Project")
    service.add_source_chapter(
        project,
        title="Chapter 1",
        chapter_number=1,
        raw_text="Nhân vật chính bước vào căn nhà hoang. "
        "Anh ta phát hiện một manh mối kỳ lạ trên sàn.",
    )
    return project, service


class TestExportPrompt:
    def test_export_all_steps_have_template_and_input(self, project_with_chapter):
        project, ps = project_with_chapter
        service = ManualAIService(ps)

        for step in SUPPORTED_STEPS:
            kwargs = {"step": step}
            if step in ("parse-story", "plan-episode"):
                kwargs["chapter_id"] = project.source_chapters[0].chapter_id
            else:
                # Các step sau cần episode — skip nếu chưa có
                continue

            exported = service.export_prompt(project, **kwargs)
            assert "prompt_template" in exported
            assert "input_data" in exported
            assert exported["step"] == step
            assert len(exported["prompt_template"]) > 0

    def test_format_for_clipboard(self, project_with_chapter):
        project, ps = project_with_chapter
        service = ManualAIService(ps)
        exported = service.export_prompt(
            project,
            step="parse-story",
            chapter_id=project.source_chapters[0].chapter_id,
        )
        text = service.format_prompt_for_clipboard(exported)
        assert "## Runtime input" in text
        assert "```json" in text

    def test_unsupported_step_raises(self, project_with_chapter):
        project, ps = project_with_chapter
        service = ManualAIService(ps)
        with pytest.raises(ValueError, match="Unsupported step"):
            service.export_prompt(project, step="invalid-step")


class TestImportResult:
    def test_import_parse_result(self, project_with_chapter):
        project, ps = project_with_chapter
        service = ManualAIService(ps)
        result = {
            "chapter_id": project.source_chapters[0].chapter_id,
            "detected_characters": [
                {"name": "Nhân vật chính", "role": "protagonist", "evidence": "test"}
            ],
            "detected_locations": [{"name": "Căn nhà hoang", "mood": "mysterious"}],
            "scene_candidates": [
                {
                    "title": "Scene test",
                    "summary": "Test summary",
                    "importance": "high",
                    "characters": ["Nhân vật chính"],
                    "location": "Căn nhà hoang",
                    "mood": "mysterious",
                    "scene_id": "sc_001",
                }
            ],
            "important_events": [
                {
                    "event_id": "ev_001",
                    "summary": "Test event",
                    "characters": ["Nhân vật chính"],
                    "location": "Căn nhà hoang",
                    "evidence": "test",
                    "importance": "medium",
                }
            ],
        }
        message = service.import_result(
            project,
            step="parse-story",
            result_data=result,
            chapter_id=project.source_chapters[0].chapter_id,
        )
        assert "Imported" in message
        assert "1 scenes" in message

    def test_import_plan_result(self, project_with_chapter):
        project, ps = project_with_chapter
        service = ManualAIService(ps)
        chapter_id = project.source_chapters[0].chapter_id
        result = {
            "episode": {
                "episode_title": "Test Episode",
                "episode_summary": "Test summary",
                "source_chapter_ids": [chapter_id],
                "tone": "mysterious",
                "density": "full",
                "hook": "Test hook",
            },
            "scenes": [
                {
                    "scene_id": "sc_test_001",
                    "title": "Test scene",
                    "summary": "Scene summary",
                    "mood": "tense",
                    "characters": ["protagonist"],
                    "location": "location",
                    "target_beats": 3,
                    "importance": "high",
                }
            ],
            "cliffhanger": "Test cliffhanger",
        }
        message = service.import_result(
            project,
            step="plan-episode",
            result_data=result,
            chapter_id=chapter_id,
        )
        assert "Imported episode" in message
        assert len(project.review_episodes) > 0
