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

    def test_build_prompts_runtime_input_is_compact(self):
        ps = ProjectService()
        project = ps.create_project("Prompt Compact", default_art_style="style_001")
        chapter = ps.add_source_chapter(
            project,
            title="Chapter",
            chapter_number=1,
            raw_text="Original source text should stay outside prompt-image payload.",
        )
        ps.add_character(
            project,
            character_id="char_used",
            name="Used Hero",
            visual_prompt_base="young hero with black hair",
            default_outfit="plain black robe",
            appearance="calm face",
            hair="black hair",
            eyes="dark eyes",
            negative_prompt_terms=["wrong robe"],
        )
        ps.add_character(
            project,
            character_id="char_unused",
            name="Unused Character",
            visual_prompt_base="very long unused character prompt",
        )
        ps.add_location(
            project,
            location_id="loc_used",
            name="Used Room",
            visual_prompt_base="small wooden room",
            lighting="soft window light",
            mood="quiet",
            description="plain interior",
            negative_prompt_terms=["modern furniture"],
        )
        ps.add_location(
            project,
            location_id="loc_unused",
            name="Unused Location",
            visual_prompt_base="very long unused location prompt",
        )
        ps.add_style_preset(
            project,
            style_id="style_001",
            name="Compact Style",
            positive_prompt="clean webtoon style",
            negative_prompt="low quality",
            forbidden_terms=["watermark", "logo"],
        )
        episode = ps.add_review_episode(
            project,
            title="Episode",
            source_chapter_ids=[chapter.chapter_id],
            episode_id="ep_001",
        )
        scene = ps.add_scene(
            project,
            episode_id=episode.episode_id,
            scene_id="sc_001",
            title="Room Scene",
            summary="Hero wakes in a room.",
            characters=["char_used"],
            location="loc_used",
            mood="quiet",
        )
        ps.add_beat(
            project,
            episode_id=episode.episode_id,
            scene_id=scene.scene_id,
            beat_id="beat_sc_001_001",
            order_index=1,
            characters=["char_used"],
            location="loc_used",
            action="opens his eyes in the wooden room",
            emotion="confused",
            shot_type="close-up",
            visual_description="a young hero wakes beside a wooden bed",
            review_text="Đây là phần review rất dài dùng để AI hiểu ngữ cảnh nhưng không nên bị dump toàn bộ vào prompt ảnh.",
            image_prompt="old prompt should not be sent back",
            negative_prompt="old negative should not be sent back",
            continuity_tags=["room", "wakeup"],
        )

        exported = ManualAIService(ps).export_prompt(
            project,
            step="build-prompts",
            episode_id=episode.episode_id,
            style_preset_id="style_001",
        )
        input_data = exported["input_data"]

        assert input_data["task"] == "build concise English image prompts for existing beats only"
        assert [item["character_id"] for item in input_data["character_bible"]] == ["char_used"]
        assert [item["location_id"] for item in input_data["location_bible"]] == ["loc_used"]

        scene_payload = input_data["scenes"][0]
        assert "beats" not in scene_payload["scene"]
        assert scene_payload["scene"]["beat_count"] == 1

        beat_payload = scene_payload["beats"][0]
        assert "image_prompt" not in beat_payload
        assert "negative_prompt" not in beat_payload
        assert "images" not in beat_payload
        assert "dialogues" not in beat_payload
        assert "source_refs" not in beat_payload
        assert "status" not in beat_payload
        assert "review_text" not in beat_payload
        assert "review_text_excerpt" in beat_payload

    def test_build_prompts_clipboard_omits_unused_bible_data(self):
        ps = ProjectService()
        project = ps.create_project("Prompt Clipboard", default_art_style="style_001")
        chapter = ps.add_source_chapter(project, title="Chapter", chapter_number=1, raw_text="Source")
        ps.add_character(
            project,
            character_id="char_used",
            name="Used Hero",
            visual_prompt_base="used hero anchor",
        )
        ps.add_character(
            project,
            character_id="char_unused",
            name="Unused Character",
            visual_prompt_base="unused character anchor should not appear",
        )
        ps.add_location(
            project,
            location_id="loc_used",
            name="Used Room",
            visual_prompt_base="used room anchor",
        )
        ps.add_style_preset(
            project,
            style_id="style_001",
            name="Compact Style",
            positive_prompt="clean webtoon style",
        )
        episode = ps.add_review_episode(
            project,
            title="Episode",
            source_chapter_ids=[chapter.chapter_id],
            episode_id="ep_001",
        )
        scene = ps.add_scene(
            project,
            episode_id=episode.episode_id,
            scene_id="sc_001",
            title="Room",
            characters=["char_used"],
            location="loc_used",
        )
        ps.add_beat(
            project,
            episode_id=episode.episode_id,
            scene_id=scene.scene_id,
            beat_id="beat_001",
            characters=["char_used"],
            location="loc_used",
            action="looks around",
            visual_description="hero inside a room",
        )

        service = ManualAIService(ps)
        prompt = service.format_prompt_for_clipboard(
            service.export_prompt(
                project,
                step="build-prompts",
                episode_id=episode.episode_id,
                style_preset_id="style_001",
            )
        )

        assert "used hero anchor" in prompt
        assert "used room anchor" in prompt
        assert "unused character anchor should not appear" not in prompt
        assert "old prompt should not be sent back" not in prompt
        runtime_input = prompt.split("## Runtime input", 1)[1]
        assert '"image_prompt": ""' not in runtime_input
        assert "45-90 words" in prompt

    def test_generation_prompt_runtime_inputs_do_not_dump_full_domain_objects(self):
        project, ps, episode = _project_with_prompt_noise()
        service = ManualAIService(ps)

        for step in ("generate-beats", "rewrite-review", "generate-unified-package"):
            exported = service.export_prompt(
                project,
                step=step,
                episode_id=episode.episode_id,
            )
            payload = exported["input_data"]
            prompt = service.format_prompt_for_clipboard(exported)
            runtime_input = prompt.split("## Runtime input", 1)[1]

            assert "old prompt should not be exported" not in runtime_input
            assert "old negative should not be exported" not in runtime_input
            assert "reference_image_paths" not in runtime_input
            assert "character_embedding_hash" not in runtime_input
            assert "ip_adapter_image_path" not in runtime_input
            assert "related_scene_ids" not in runtime_input
            assert "source_refs" not in runtime_input
            assert "images" not in runtime_input
            assert "dialogues" not in runtime_input
            assert "status" not in runtime_input
            assert payload

    def test_parse_and_plan_prompts_use_compact_bible_context(self):
        project, ps, _episode = _project_with_prompt_noise()
        chapter_id = project.source_chapters[0].chapter_id
        service = ManualAIService(ps)

        for step in ("parse-story", "plan-episode"):
            prompt = service.format_prompt_for_clipboard(
                service.export_prompt(project, step=step, chapter_id=chapter_id)
            )
            runtime_input = prompt.split("## Runtime input", 1)[1]

            assert "noisy reference note" not in runtime_input
            assert "reference_image_paths" not in runtime_input
            assert "character_embedding_hash" not in runtime_input
            assert "related_scene_ids" not in runtime_input
            assert "used hero anchor" in runtime_input
            assert "used room anchor" in runtime_input


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


def _project_with_prompt_noise():
    ps = ProjectService()
    project = ps.create_project("Noisy Prompt Project", default_art_style="style_001")
    chapter = ps.add_source_chapter(
        project,
        title="Chapter",
        chapter_number=1,
        raw_text="The used hero wakes in the used room and notices a strange symbol.",
    )
    character = ps.add_character(
        project,
        character_id="char_used",
        name="Used Hero",
        visual_prompt_base="used hero anchor",
        default_outfit="black robe",
        appearance="focused young cultivator",
        reference_image_note="noisy reference note",
    )
    character.reference_image_paths = ["unused/path.png"]
    character.character_embedding_hash = "hash_should_not_export"
    character.ip_adapter_image_path = "adapter_should_not_export.png"
    ps.add_location(
        project,
        location_id="loc_used",
        name="Used Room",
        visual_prompt_base="used room anchor",
        description="small wooden bedroom",
        related_scene_ids=["old_scene_should_not_export"],
    )
    ps.add_style_preset(
        project,
        style_id="style_001",
        name="Compact Style",
        positive_prompt="clean webtoon style",
        negative_prompt="low quality",
        forbidden_terms=["watermark", "logo"],
    )
    episode = ps.add_review_episode(
        project,
        title="Episode",
        source_chapter_ids=[chapter.chapter_id],
        episode_id="ep_001",
        summary="Hero wakes.",
    )
    scene = ps.add_scene(
        project,
        episode_id=episode.episode_id,
        scene_id="sc_001",
        title="Wakeup",
        summary="Hero wakes in a small room.",
        characters=["char_used"],
        location="loc_used",
        mood="tense",
        target_beats=3,
    )
    ps.add_beat(
        project,
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        beat_id="beat_001",
        order_index=1,
        source_refs=[chapter.chapter_id],
        story_function="discovery",
        characters=["char_used"],
        location="loc_used",
        action="opens his eyes",
        emotion="confused",
        shot_type="close-up",
        visual_description="hero beside a wooden bed",
        review_text="Đây là review text cũ chỉ nên dùng khi thật sự cần.",
        image_prompt="old prompt should not be exported",
        negative_prompt="old negative should not be exported",
        continuity_tags=["wakeup"],
        status="reviewed",
    )
    return project, ps, episode
