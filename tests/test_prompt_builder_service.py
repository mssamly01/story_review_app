import unittest

from app.domain.character import CharacterOutfit, CharacterVariant
from app.services.project_service import ProjectService
from app.services.prompt_builder_service import PromptBuilderService


def build_prompt_project(*, include_style: bool = True):
    project_service = ProjectService()
    project = project_service.create_project(
        "Can nha cu",
        default_art_style="dark fantasy webtoon",
    )
    chapter = project_service.add_source_chapter(
        project,
        title="Chapter 1",
        chapter_number=1,
        raw_text="Lam Vu tro ve can nha cu va nghe tieng dong la.",
    )
    character = project_service.add_character(
        project,
        character_id="lam_vu",
        name="Lam Vu",
        appearance="character with multiple forms across timelines",
        default_outfit="black jacket, white shirt",
        visual_prompt_base="young man, messy black hair, gray eyes, black jacket, white shirt",
    )
    character.variants = [
        CharacterVariant(
            variant_id="lam_vu_young",
            character_id="lam_vu",
            display_name="Lam Vu - young form",
            age_stage="child",
            age_description="appears 10 years old",
            hair="messy black hair",
            eyes="sharp mature dark eyes",
            body_type="slim child body",
            visual_prompt_base=(
                "10-year-old fantasy boy, slim child body, messy black hair, "
                "sharp mature dark eyes"
            ),
            negative_prompt_terms=["old man", "white hair", "adult body"],
            default_outfit_id="outfit_lam_vu_young_inner_robe",
        ),
        CharacterVariant(
            variant_id="lam_vu_old",
            character_id="lam_vu",
            display_name="Lam Vu - old form",
            age_stage="old",
            age_description="over 500 years old",
            hair="long white hair",
            eyes="tired hatred-filled eyes",
            body_type="aged exhausted cultivator body",
            visual_prompt_base=(
                "old male cultivator over 500 years old, long white hair, "
                "aged exhausted face"
            ),
            negative_prompt_terms=["young boy", "black hair", "child body"],
            default_outfit_id="outfit_lam_vu_old_battle_robe",
        ),
    ]
    character.outfits = [
        CharacterOutfit(
            outfit_id="outfit_lam_vu_young_inner_robe",
            character_id="lam_vu",
            variant_id="lam_vu_young",
            display_name="Blue gray inner robe",
            outfit_type="sleepwear",
            description="simple blue-gray ancient inner robe, loose cloth fabric",
            colors=["blue-gray", "dark brown"],
            negative_prompt_terms=["modern clothes", "armor"],
        ),
        CharacterOutfit(
            outfit_id="outfit_lam_vu_old_battle_robe",
            character_id="lam_vu",
            variant_id="lam_vu_old",
            display_name="Torn battle robe",
            outfit_type="battle",
            description="torn ancient battle robe with blood stains",
            colors=["dark gray", "blood red"],
            negative_prompt_terms=["clean robe", "child sleepwear"],
        ),
    ]
    location = project_service.add_location(
        project,
        location_id="old_house_hallway",
        name="Old House Hallway",
        visual_prompt_base="dusty old hallway, wooden floor, dim moonlight",
        mood="dark, silent, mysterious",
        lighting="dim moonlight",
    )
    if include_style:
        style = project_service.add_style_preset(
            project,
            style_id="dark_fantasy_webtoon",
            name="Dark Fantasy Webtoon",
            positive_prompt="dark fantasy webtoon style, cinematic lighting, detailed background",
            negative_prompt="flat lighting, inconsistent style, watermark, text",
            lighting="moonlight, rim light, deep shadows",
            background_detail="high",
        )
    else:
        style = None
    episode = project_service.add_review_episode(
        project,
        title="Canh cua cuoi hanh lang",
        source_chapter_ids=[chapter.chapter_id],
        tone="mysterious",
        density="full",
    )
    scene = project_service.add_scene(
        project,
        episode_id=episode.episode_id,
        title="Tro ve nha cu",
        summary="Lam Vu buoc vao hanh lang toi va nhin thay dau chan moi.",
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
        character_variants={"lam_vu": "lam_vu_young"},
        character_outfits={"lam_vu": "outfit_lam_vu_young_inner_robe"},
        location=location.location_id,
        action="discovers fresh footprints in the dusty hallway",
        emotion="uneasy",
        shot_type="low angle close-up",
        review_text="Lam Vu phat hien dau chan moi truoc can phong bi khoa.",
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
        self.assertIn("Old House Hallway", beat.image_prompt)
        self.assertIn("discovers fresh footprints", beat.image_prompt)
        self.assertIn("uneasy", beat.image_prompt)
        self.assertIn("low angle close-up", beat.image_prompt)
        self.assertIn("one clear visual moment", beat.image_prompt)

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
            title="Can phong bi khoa",
            summary="Canh cua cu rung len du khong co ai cham vao.",
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
            "high quality comic/webtoon illustration style, clean line art, detailed background",
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

        self.assertIn("simple blue-gray ancient inner robe", beat.image_prompt)

    def test_prompt_builder_uses_variant_not_generic_character(self) -> None:
        sample = build_prompt_project()
        project = sample["project"]
        beat = sample["beat"]
        beat.character_variants = {"lam_vu": "lam_vu_young"}
        beat.character_outfits = {"lam_vu": "outfit_lam_vu_young_inner_robe"}

        PromptBuilderService().build_prompt_for_beat(project, beat.beat_id)
        prompt = beat.image_prompt

        self.assertIn("slim child body", prompt)
        self.assertIn("messy black hair", prompt)
        self.assertNotIn("long white hair", prompt)
        self.assertNotIn("aged exhausted cultivator body", prompt)

    def test_prompt_builder_uses_selected_outfit(self) -> None:
        sample = build_prompt_project()
        project = sample["project"]
        beat = sample["beat"]
        beat.character_variants = {"lam_vu": "lam_vu_young"}
        beat.character_outfits = {"lam_vu": "outfit_lam_vu_young_inner_robe"}

        PromptBuilderService().build_prompt_for_beat(project, beat.beat_id)
        prompt = beat.image_prompt

        self.assertIn("simple blue-gray ancient inner robe", prompt)
        self.assertNotIn("torn ancient battle robe", prompt)

    def test_prompt_builder_old_variant_uses_old_form(self) -> None:
        sample = build_prompt_project()
        project = sample["project"]
        beat = sample["beat"]
        beat.character_variants = {"lam_vu": "lam_vu_old"}
        beat.character_outfits = {"lam_vu": "outfit_lam_vu_old_battle_robe"}

        PromptBuilderService().build_prompt_for_beat(project, beat.beat_id)
        prompt = beat.image_prompt

        self.assertIn("long white hair", prompt)
        self.assertIn("aged exhausted cultivator body", prompt)
        self.assertIn("torn ancient battle robe", prompt)
        self.assertNotIn("slim child body", prompt)
        self.assertNotIn("simple blue-gray ancient inner robe", prompt)

    def test_negative_prompt_includes_variant_and_outfit_negatives(self) -> None:
        sample = build_prompt_project()
        project = sample["project"]
        beat = sample["beat"]
        beat.character_variants = {"lam_vu": "lam_vu_old"}
        beat.character_outfits = {"lam_vu": "outfit_lam_vu_old_battle_robe"}

        PromptBuilderService().build_prompt_for_beat(project, beat.beat_id)
        terms = [term.strip() for term in beat.negative_prompt.split(",")]

        self.assertIn("young boy", terms)
        self.assertIn("black hair", terms)
        self.assertIn("child body", terms)
        self.assertIn("clean robe", terms)
        self.assertIn("child sleepwear", terms)

    def test_prompt_builder_uses_episode_planner_storyboard_fields(self) -> None:
        sample = build_prompt_project()
        project = sample["project"]
        beat = sample["beat"]
        beat.camera = "slow dolly-in from floor level"
        beat.timeOfDay = "Night"
        beat.lighting = "thin moonlight and candle flicker"
        beat.atmosphere = "cold mist in the hallway"
        beat.location_cues = "fresh footprints crossing dusty boards"
        beat.asmr_visuals = "floating dust, candle flicker, trembling curtain"
        beat.composition = "footprints leading toward a locked door"
        beat.posture = "half crouched beside the floor"
        beat.expression = "uneasy focused stare"
        beat.body_language = "one hand hovering above the footprints"
        beat.props = ["rusty key", "loose floorboard"]
        beat.wardrobe_notes = "black jacket still damp from rain"
        beat.character_state = "tired but alert"
        beat.location_state = "old hallway freshly disturbed"
        beat.transition_note = "before the hidden letter reveal"
        service = PromptBuilderService()

        service.build_prompt_for_beat(project, beat.beat_id)

        for expected in [
            "slow dolly-in from floor level",
            "Night",
            "thin moonlight and candle flicker",
            "cold mist in the hallway",
            "fresh footprints crossing dusty boards",
            "floating dust, candle flicker, trembling curtain",
            "footprints leading toward a locked door",
            "half crouched beside the floor",
            "uneasy focused stare",
            "one hand hovering above the footprints",
            "rusty key",
            "loose floorboard",
            "black jacket still damp from rain",
            "Current state: tired but alert",
            "old hallway freshly disturbed",
            "before the hidden letter reveal",
        ]:
            self.assertIn(expected, beat.image_prompt)


    def test_prompt_builder_uses_base_profile_for_single_form_character(self):
        project_service = ProjectService()
        project = project_service.create_project("Test Single Form")
        char = project_service.add_character(
            project, character_id="char_002", name="Tang Thien Co",
            hair="Long Black", eyes="Sharp"
        )
        # New rule: no variants created by default
        self.assertEqual(len(char.variants), 0)
        
        episode = project_service.add_review_episode(project, title="Ep 1", source_chapter_ids=[])
        scene = project_service.add_scene(project, episode_id=episode.episode_id, title="Sc 1")
        beat = project_service.add_beat(project, episode_id=episode.episode_id, scene_id=scene.scene_id)
        beat.characters = ["char_002"]
        
        service = PromptBuilderService()
        service.build_prompt_for_beat(project, beat.beat_id)
        
        # Should include fields from the base character
        self.assertIn("Long Black", beat.image_prompt)
        self.assertIn("Sharp", beat.image_prompt)
        self.assertIn("Tang Thien Co", beat.image_prompt)


if __name__ == "__main__":
    unittest.main()
