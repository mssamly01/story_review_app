import unittest

from app.services.project_service import ProjectService
from app.services.prompt_builder_service import PromptBuilderService


def build_prompt_project(*, include_style: bool = True):
    project_service = ProjectService()
    project = project_service.create_project(
        "Căn nhà cũ",
        default_art_style="dark fantasy webtoon",
    )
    chapter = project_service.add_source_chapter(
        project,
        title="Chương 1",
        chapter_number=1,
        raw_text="Lâm Vũ trở về căn nhà cũ và nghe tiếng động lạ.",
    )
    character = project_service.add_character(
        project,
        character_id="lam_vu",
        name="Lâm Vũ",
        appearance="young man, messy black hair, gray eyes",
        default_outfit="black jacket, white shirt",
        visual_prompt_base=("young man, messy black hair, gray eyes, black jacket, white shirt"),
    )
    location = project_service.add_location(
        project,
        location_id="old_house_hallway",
        name="Hành lang nhà cũ",
        visual_prompt_base="dusty old hallway, wooden floor, dim moonlight",
        mood="dark, silent, mysterious",
        lighting="dim moonlight",
    )
    if include_style:
        style = project_service.add_style_preset(
            project,
            style_id="dark_fantasy_webtoon",
            name="Dark Fantasy Webtoon",
            positive_prompt=("dark fantasy webtoon style, cinematic lighting, detailed background"),
            negative_prompt="flat lighting, inconsistent style, watermark, text",
            lighting="moonlight, rim light, deep shadows",
            background_detail="high",
        )
    else:
        style = None
    episode = project_service.add_review_episode(
        project,
        title="Cánh cửa cuối hành lang",
        source_chapter_ids=[chapter.chapter_id],
        tone="mysterious",
        density="full",
    )
    scene = project_service.add_scene(
        project,
        episode_id=episode.episode_id,
        title="Trở về nhà cũ",
        summary="Lâm Vũ bước vào hành lang tối và nhìn thấy dấu chân mới.",
        characters=[character.character_id],
        location=location.location_id,
        mood="mysterious",
    )
    beat = project_service.add_beat(
        project,
        episode_id=episode.episode_id,
        scene_id=scene.scene_id,
        beat_id="b_001",
        order_index=1,
        story_function="discovery",
        characters=[character.character_id],
        location=location.location_id,
        action="discovers fresh footprints in the dusty hallway",
        emotion="uneasy",
        shot_type="low angle close-up",
        review_text="Lâm Vũ phát hiện dấu chân mới trước căn phòng bị khóa.",
        visual_description="fresh footprints on dusty wooden floor near a locked door",
        continuity_tags=["lam_vu", "old_house_hallway", "night"],
    )
    return {
        "project_service": project_service,
        "project": project,
        "chapter": chapter,
        "character": character,
        "location": location,
        "style": style,
        "episode": episode,
        "scene": scene,
        "beat": beat,
    }


class PromptBuilderServiceTests(unittest.TestCase):
    def test_build_prompt_for_single_beat(self) -> None:
        sample = build_prompt_project()
        project = sample["project"]
        beat = sample["beat"]
        service = PromptBuilderService()

        prompted_beat = service.build_prompt_for_beat(project, beat.beat_id)

        self.assertIs(prompted_beat, beat)
        self.assertNotEqual(beat.image_prompt, "")
        self.assertNotEqual(beat.negative_prompt, "")
        self.assertIn("dark fantasy webtoon style", beat.image_prompt)
        self.assertIn(
            "young man, messy black hair, gray eyes, black jacket, white shirt",
            beat.image_prompt,
        )
        self.assertIn(
            "dusty old hallway, wooden floor, dim moonlight",
            beat.image_prompt,
        )
        self.assertIn("discovers fresh footprints", beat.image_prompt)
        self.assertIn("uneasy", beat.image_prompt)
        self.assertIn("low angle close-up", beat.image_prompt)
        self.assertIn("fresh footprints on dusty wooden floor", beat.image_prompt)
        self.assertIn("single clear visual moment", beat.image_prompt)
        self.assertIn("cinematic lighting", beat.image_prompt)

    def test_build_prompts_for_scene(self) -> None:
        sample = build_prompt_project()
        project = sample["project"]
        project_service = sample["project_service"]
        episode = sample["episode"]
        scene = sample["scene"]
        project_service.add_beat(
            project,
            episode_id=episode.episode_id,
            scene_id=scene.scene_id,
            beat_id="b_002",
            order_index=2,
            characters=["lam_vu"],
            location="old_house_hallway",
            action="listens to a strange sound behind the locked door",
            emotion="tense",
            shot_type="close-up",
            visual_description="tense face beside an old locked door",
        )
        service = PromptBuilderService()

        prompted_beats = service.build_prompts_for_scene(project, scene.scene_id)

        self.assertEqual(prompted_beats, scene.ordered_beats())
        self.assertTrue(all(beat.image_prompt for beat in scene.beats))
        self.assertTrue(all(beat.negative_prompt for beat in scene.beats))

    def test_build_prompts_for_episode(self) -> None:
        sample = build_prompt_project()
        project = sample["project"]
        project_service = sample["project_service"]
        episode = sample["episode"]
        second_scene = project_service.add_scene(
            project,
            episode_id=episode.episode_id,
            title="Căn phòng bị khóa",
            summary="Cánh cửa cũ rung lên dù không có ai chạm vào.",
            characters=["lam_vu"],
            location="old_house_hallway",
            mood="tense",
        )
        project_service.add_beat(
            project,
            episode_id=episode.episode_id,
            scene_id=second_scene.scene_id,
            beat_id="b_002",
            order_index=1,
            characters=["lam_vu"],
            location="old_house_hallway",
            action="the locked door shakes by itself",
            emotion="shocked",
            shot_type="extreme close-up",
            visual_description="old brass lock trembling in the dark",
        )
        service = PromptBuilderService()

        prompted_beats = service.build_prompts_for_episode(project, episode.episode_id)

        self.assertEqual(len(prompted_beats), 2)
        self.assertTrue(all(beat.image_prompt for beat in prompted_beats))
        self.assertTrue(all(beat.negative_prompt for beat in prompted_beats))

    def test_prompt_builder_does_not_modify_review_text(self) -> None:
        sample = build_prompt_project()
        project = sample["project"]
        beat = sample["beat"]
        review_text = beat.review_text
        service = PromptBuilderService()

        service.build_prompt_for_beat(project, beat.beat_id)

        self.assertEqual(beat.review_text, review_text)

    def test_prompt_builder_does_not_modify_source_raw_text(self) -> None:
        sample = build_prompt_project()
        project = sample["project"]
        chapter = sample["chapter"]
        raw_text = chapter.raw_text
        service = PromptBuilderService()

        service.build_prompts_for_episode(project, sample["episode"].episode_id)

        self.assertEqual(chapter.raw_text, raw_text)

    def test_prompt_builder_is_idempotent(self) -> None:
        sample = build_prompt_project()
        project = sample["project"]
        beat = sample["beat"]
        service = PromptBuilderService()

        service.build_prompt_for_beat(project, beat.beat_id)
        first_prompt = beat.image_prompt
        first_negative = beat.negative_prompt
        service.build_prompt_for_beat(project, beat.beat_id)

        self.assertEqual(beat.image_prompt, first_prompt)
        self.assertEqual(beat.negative_prompt, first_negative)

    def test_prompt_builder_uses_default_style_when_missing(self) -> None:
        sample = build_prompt_project(include_style=False)
        project = sample["project"]
        beat = sample["beat"]
        service = PromptBuilderService()

        service.build_prompt_for_beat(project, beat.beat_id)

        self.assertIn(
            "cinematic webtoon style, high quality illustration",
            beat.image_prompt,
        )

    def test_prompt_builder_avoids_text_in_image(self) -> None:
        sample = build_prompt_project()
        project = sample["project"]
        beat = sample["beat"]
        service = PromptBuilderService()

        service.build_prompt_for_beat(project, beat.beat_id)

        lowered_prompt = beat.image_prompt.lower()
        for blocked_term in [
            "subtitles",
            "captions",
            "speech bubbles",
            "watermark",
            "logo",
        ]:
            self.assertNotIn(blocked_term, lowered_prompt)

        for negative_term in ["text", "watermark", "logo"]:
            self.assertIn(negative_term, beat.negative_prompt)

    def test_prompt_builder_preserves_character_consistency(self) -> None:
        sample = build_prompt_project()
        project = sample["project"]
        beat = sample["beat"]
        service = PromptBuilderService()

        service.build_prompt_for_beat(project, beat.beat_id)

        self.assertIn("black jacket, white shirt", beat.image_prompt)


if __name__ == "__main__":
    unittest.main()
