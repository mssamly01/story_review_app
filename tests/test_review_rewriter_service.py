import unittest

from app.services.project_service import ProjectService
from app.services.review_rewriter_service import ReviewRewriterService


def build_rewriter_project():
    project_service = ProjectService()
    project = project_service.create_project("Căn nhà cũ")
    chapter = project_service.add_source_chapter(
        project,
        title="Chương 1",
        chapter_number=1,
        raw_text=("Lâm Vũ trở về căn nhà cũ. " "Anh nghe thấy tiếng động sau cánh cửa bị khóa."),
    )
    episode = project_service.add_review_episode(
        project,
        title="Cánh cửa cuối hành lang",
        source_chapter_ids=[chapter.chapter_id],
        tone="mysterious",
        density="balanced",
    )
    first_scene = project_service.add_scene(
        project,
        episode_id=episode.episode_id,
        title="Trở về nhà cũ",
        summary=("Lâm Vũ quay lại căn nhà cũ và nhận ra hành lang phía sau " "vẫn tối bất thường."),
        characters=["lam_vu"],
        location="old_house_hallway",
        mood="mysterious",
        importance="high",
        target_beats=6,
    )
    second_scene = project_service.add_scene(
        project,
        episode_id=episode.episode_id,
        title="Cánh cửa bị khóa",
        summary="Lâm Vũ đứng trước cánh cửa bị khóa và nghe tiếng động lạ.",
        characters=["lam_vu"],
        location="locked_room_door",
        mood="tense",
        importance="medium",
        target_beats=4,
    )
    first_beat = project_service.add_beat(
        project,
        episode_id=episode.episode_id,
        scene_id=first_scene.scene_id,
        beat_id="b_001",
        order_index=1,
        source_refs=[chapter.chapter_id],
        story_function="discovery",
        characters=["lam_vu"],
        location="old_house_hallway",
        action="Lâm Vũ phát hiện hành lang phủ bụi nhưng có dấu chân mới",
        emotion="suspicious",
        shot_type="detail shot",
        visual_description="dấu chân mới trên nền bụi trước hành lang tối",
        image_prompt="existing image prompt should remain unchanged",
        negative_prompt="existing negative prompt should remain unchanged",
        continuity_tags=["sc_001", "lam_vu", "old_house_hallway", "night"],
    )
    second_beat = project_service.add_beat(
        project,
        episode_id=episode.episode_id,
        scene_id=first_scene.scene_id,
        beat_id="b_002",
        order_index=2,
        source_refs=[chapter.chapter_id],
        story_function="reaction",
        characters=["lam_vu"],
        location="old_house_hallway",
        action="anh dừng lại và lắng nghe tiếng động phía cuối hành lang",
        emotion="tense",
        shot_type="close-up",
        visual_description="gương mặt căng thẳng của Lâm Vũ trong bóng tối",
        continuity_tags=["sc_001", "lam_vu", "old_house_hallway", "night"],
    )
    third_beat = project_service.add_beat(
        project,
        episode_id=episode.episode_id,
        scene_id=second_scene.scene_id,
        beat_id="b_003",
        order_index=1,
        source_refs=[chapter.chapter_id],
        story_function="cliffhanger",
        characters=["lam_vu"],
        location="locked_room_door",
        action="cánh cửa bị khóa rung lên dù không có ai chạm vào",
        emotion="shocked",
        shot_type="extreme close-up",
        visual_description="ổ khóa cũ rung nhẹ trong bóng tối",
        continuity_tags=["sc_002", "locked_room_door", "night"],
    )
    return {
        "project_service": project_service,
        "project": project,
        "chapter": chapter,
        "episode": episode,
        "first_scene": first_scene,
        "second_scene": second_scene,
        "beats": [first_beat, second_beat, third_beat],
    }


class ReviewRewriterServiceTests(unittest.TestCase):
    def test_rewrite_single_beat_generates_review_text(self) -> None:
        sample = build_rewriter_project()
        project = sample["project"]
        beat = sample["beats"][0]
        service = ReviewRewriterService()

        rewritten_beat = service.rewrite_beat(project, beat.beat_id)

        self.assertIs(rewritten_beat, beat)
        self.assertNotEqual(beat.review_text, "")
        self.assertIn("Lâm Vũ", beat.review_text)
        self.assertIn("hành lang", beat.review_text)
        self.assertIn("nghi ngờ", beat.review_text)
        self.assertIn("không gộp chung", beat.review_text)
        self.assertIn("Về mặt hình ảnh", beat.review_text)
        self.assertGreater(len(beat.review_text.split()), 35)

    def test_rewrite_scene_updates_all_scene_beats(self) -> None:
        sample = build_rewriter_project()
        project = sample["project"]
        first_scene = sample["first_scene"]
        service = ReviewRewriterService()

        rewritten_beats = service.rewrite_scene(project, first_scene.scene_id)

        self.assertEqual(rewritten_beats, first_scene.ordered_beats())
        self.assertTrue(all(beat.review_text for beat in first_scene.beats))
        self.assertEqual(sample["beats"][2].review_text, "")

    def test_rewrite_episode_updates_all_episode_beats(self) -> None:
        sample = build_rewriter_project()
        project = sample["project"]
        episode = sample["episode"]
        service = ReviewRewriterService()

        rewritten_beats = service.rewrite_episode(project, episode.episode_id)

        self.assertEqual(len(rewritten_beats), 3)
        self.assertTrue(all(beat.review_text for beat in sample["beats"]))

    def test_rewrite_does_not_modify_source_raw_text(self) -> None:
        sample = build_rewriter_project()
        project = sample["project"]
        episode = sample["episode"]
        chapter = sample["chapter"]
        raw_text = chapter.raw_text
        service = ReviewRewriterService()

        service.rewrite_episode(project, episode.episode_id)

        self.assertEqual(chapter.raw_text, raw_text)

    def test_rewrite_does_not_generate_image_prompts(self) -> None:
        sample = build_rewriter_project()
        project = sample["project"]
        episode = sample["episode"]
        first_beat = sample["beats"][0]
        second_beat = sample["beats"][1]
        original_prompt = first_beat.image_prompt
        original_negative_prompt = first_beat.negative_prompt
        service = ReviewRewriterService()

        service.rewrite_episode(project, episode.episode_id)

        self.assertEqual(first_beat.image_prompt, original_prompt)
        self.assertEqual(first_beat.negative_prompt, original_negative_prompt)
        self.assertEqual(second_beat.image_prompt, "")
        self.assertEqual(second_beat.negative_prompt, "")

    def test_rewrite_is_idempotent(self) -> None:
        sample = build_rewriter_project()
        project = sample["project"]
        beat = sample["beats"][0]
        service = ReviewRewriterService()

        first = service.rewrite_beat(project, beat.beat_id).review_text
        second = service.rewrite_beat(project, beat.beat_id).review_text

        self.assertEqual(first, second)

    def test_narration_style_affects_output(self) -> None:
        sample = build_rewriter_project()
        project = sample["project"]
        beat = sample["beats"][0]
        service = ReviewRewriterService()

        mysterious = service.rewrite_beat(
            project,
            beat.beat_id,
            narration_style="mysterious",
        ).review_text
        dramatic = service.rewrite_beat(
            project,
            beat.beat_id,
            narration_style="dramatic",
        ).review_text
        friendly = service.rewrite_beat(
            project,
            beat.beat_id,
            narration_style="friendly",
        ).review_text
        fast_paced = service.rewrite_beat(
            project,
            beat.beat_id,
            narration_style="fast-paced",
        ).review_text

        self.assertIn("giấu một điều bất thường", mysterious)
        self.assertIn("đẩy lên một nấc căng hơn", dramatic)
        self.assertIn("người xem theo chân", friendly)
        self.assertIn("chuyển nhanh", fast_paced)
        self.assertEqual(len({mysterious, dramatic, friendly, fast_paced}), 4)

    def test_retelling_density_affects_length(self) -> None:
        sample = build_rewriter_project()
        project = sample["project"]
        beat = sample["beats"][0]
        service = ReviewRewriterService()

        full = service.rewrite_beat(
            project,
            beat.beat_id,
            retelling_density="full",
        ).review_text
        balanced = service.rewrite_beat(
            project,
            beat.beat_id,
            retelling_density="balanced",
        ).review_text
        condensed = service.rewrite_beat(
            project,
            beat.beat_id,
            retelling_density="condensed",
        ).review_text

        self.assertGreaterEqual(len(full), len(balanced))
        self.assertGreaterEqual(len(balanced), len(condensed))
        self.assertGreater(len(condensed.split()), 20)

    def test_rewrite_rejects_unknown_style_or_density(self) -> None:
        sample = build_rewriter_project()
        project = sample["project"]
        beat = sample["beats"][0]
        service = ReviewRewriterService()

        with self.assertRaises(ValueError):
            service.rewrite_beat(project, beat.beat_id, narration_style="epic")

        with self.assertRaises(ValueError):
            service.rewrite_beat(project, beat.beat_id, retelling_density="tiny")


if __name__ == "__main__":
    unittest.main()
