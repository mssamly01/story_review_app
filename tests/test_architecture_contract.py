import json
import unittest

from app.services.project_service import ProjectService


def build_contract_project():
    service = ProjectService()
    project = service.create_project(
        "Căn nhà cũ",
        project_id="project_contract",
        genre="dark fantasy",
        language="vi",
        default_narration_style="mysterious",
        default_art_style="dark fantasy webtoon",
        retelling_density="full",
    )
    chapter = service.add_source_chapter(
        project,
        chapter_id="ch_001",
        title="Chương 1",
        chapter_number=1,
        raw_text="Lâm Vũ trở về căn nhà cũ. Cánh cửa cuối hành lang bị khóa.",
        notes="Original source text pasted by the user.",
    )
    character = service.add_character(
        project,
        character_id="lam_vu",
        name="Lâm Vũ",
        role="protagonist",
        personality="calm, cautious, observant",
        appearance="young man, messy black hair, gray eyes",
        default_outfit="black jacket, white shirt",
        visual_prompt_base=(
            "young man, messy black hair, gray eyes, black jacket, white shirt"
        ),
    )
    location = service.add_location(
        project,
        location_id="old_house_hallway",
        name="Hành lang nhà cũ",
        mood="dark, silent, mysterious",
        lighting="dim moonlight",
        visual_prompt_base="dusty old hallway, wooden floor, dim moonlight",
    )
    style_preset = service.add_style_preset(
        project,
        style_id="dark_fantasy_webtoon",
        name="Dark Fantasy Webtoon",
        positive_prompt=(
            "dark fantasy webtoon style, cinematic lighting, detailed background"
        ),
        negative_prompt="low quality, blurry, watermark, text",
        lighting="moonlight, rim light, deep shadows",
        background_detail="high",
    )
    episode = service.add_review_episode(
        project,
        episode_id="ep_001",
        title="Cánh cửa cuối hành lang",
        source_chapter_ids=[chapter.chapter_id],
        tone="mysterious",
        density="full",
        summary="Detailed episode plan, not a short summary-only object.",
    )
    scene = service.add_scene(
        project,
        episode_id=episode.episode_id,
        scene_id="sc_001",
        title="Trở về nhà cũ",
        summary="Lâm Vũ bước vào căn nhà cũ và nhận ra có điều bất thường.",
        characters=[character.character_id],
        location=location.location_id,
        mood="lonely, mysterious",
        importance="high",
        target_beats=8,
    )
    first_beat = service.add_beat(
        project,
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        beat_id="b_001",
        order_index=1,
        story_function="opening",
        characters=[character.character_id],
        location=location.location_id,
        action="returns to the old house",
        emotion="uneasy",
        shot_type="wide shot",
        review_text=(
            "Sau nhiều năm xa cách, Lâm Vũ cuối cùng cũng quay lại căn nhà cũ."
        ),
        visual_description="Lâm Vũ đứng trước hành lang phủ bụi.",
        image_prompt=(
            "dark fantasy webtoon style, young man in a dusty old hallway"
        ),
        negative_prompt="low quality, blurry, watermark, text",
        continuity_tags=["lam_vu_black_jacket", "old_house_hallway"],
    )
    second_beat = service.add_beat(
        project,
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        beat_id="b_002",
        order_index=2,
        story_function="discovery",
        characters=[character.character_id],
        location=location.location_id,
        action="hears a sound behind the locked door",
        emotion="tense",
        shot_type="low angle close-up",
        review_text="Ngay sau đó, anh nghe thấy tiếng động sau cánh cửa bị khóa.",
        visual_description="Cánh cửa cũ rung nhẹ trong hành lang tối.",
        image_prompt=(
            "dark fantasy webtoon style, locked wooden door in a dusty hallway"
        ),
        negative_prompt="low quality, blurry, watermark, text",
        continuity_tags=["old_house_hallway", "locked_door"],
    )
    return {
        "service": service,
        "project": project,
        "chapter": chapter,
        "character": character,
        "location": location,
        "style_preset": style_preset,
        "episode": episode,
        "scene": scene,
        "beats": [first_beat, second_beat],
    }


class ArchitectureContractTests(unittest.TestCase):
    def test_project_model_contains_core_collections(self) -> None:
        sample = build_contract_project()
        project = sample["project"]

        self.assertEqual(len(project.source_chapters), 1)
        self.assertEqual(len(project.review_episodes), 1)
        self.assertEqual(len(project.characters), 1)
        self.assertEqual(len(project.locations), 1)
        self.assertEqual(len(project.style_presets), 1)
        self.assertEqual(len(project.review_episodes[0].scenes), 1)
        self.assertEqual(len(project.review_episodes[0].scenes[0].beats), 2)

        data = project.to_dict()
        for key in [
            "project_id",
            "title",
            "source_chapters",
            "review_episodes",
            "characters",
            "locations",
            "style_presets",
        ]:
            self.assertIn(key, data)

        json_text = json.dumps(data, ensure_ascii=False, indent=2)
        self.assertIn('\n  "project_id": "project_contract"', json_text)
        self.assertEqual(json.loads(json_text)["project_id"], "project_contract")

    def test_source_chapter_contract_preserves_raw_text(self) -> None:
        sample = build_contract_project()
        chapter = sample["chapter"]
        raw_text = chapter.raw_text

        data = chapter.to_dict()
        for key in [
            "chapter_id",
            "title",
            "chapter_number",
            "raw_text",
            "word_count",
            "notes",
        ]:
            self.assertIn(key, data)

        self.assertEqual(data["raw_text"], raw_text)
        self.assertEqual(data["word_count"], len(raw_text.split()))

        # Rewritten review content lives on Beat, never over source text.
        sample["beats"][0].review_text = "Rewritten narration belongs here."
        self.assertEqual(chapter.raw_text, raw_text)

    def test_review_episode_contract_is_structured_not_summary_only(self) -> None:
        episode = build_contract_project()["episode"]
        data = episode.to_dict()

        self.assertEqual(episode.source_chapter_ids, ["ch_001"])
        self.assertEqual(episode.scene_ids, ["sc_001"])
        self.assertEqual(episode.tone, "mysterious")
        self.assertEqual(episode.density, "full")
        self.assertIsInstance(episode.scenes, list)
        self.assertNotEqual(episode.scenes, [])
        self.assertIn("scenes", data)
        self.assertIn("source_chapter_ids", data)

    def test_scene_contract_can_hold_multiple_beats(self) -> None:
        scene = build_contract_project()["scene"]
        data = scene.to_dict()

        self.assertEqual(scene.episode_id, "ep_001")
        self.assertEqual(scene.beat_ids, ["b_001", "b_002"])
        self.assertEqual(len(scene.beats), 2)
        for key in [
            "scene_id",
            "episode_id",
            "title",
            "summary",
            "mood",
            "characters",
            "location",
            "beat_ids",
            "beats",
        ]:
            self.assertIn(key, data)

    def test_beat_contract_is_central_and_structured(self) -> None:
        beat = build_contract_project()["beats"][0]
        data = beat.to_dict()

        for key in [
            "beat_id",
            "scene_id",
            "order_index",
            "story_function",
            "characters",
            "location",
            "action",
            "emotion",
            "shot_type",
            "visual_description",
            "review_text",
            "image_prompt",
            "negative_prompt",
            "continuity_tags",
        ]:
            self.assertIn(key, data)

        self.assertEqual(beat.scene_id, "sc_001")
        self.assertEqual(beat.order_index, 1)
        self.assertNotIn("text", data)
        self.assertNotIn("content", data)
        self.assertNotEqual(beat.review_text, "")
        self.assertNotEqual(beat.image_prompt, "")


if __name__ == "__main__":
    unittest.main()
