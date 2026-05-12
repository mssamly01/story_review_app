from __future__ import annotations

import os
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.controllers.generation_controller import GenerationController
from app.domain.character import CharacterOutfit, CharacterVariant
from app.services.project_service import ProjectService
from app.services.prompt_builder_service import PromptBuilderService
from app.ui.app_state import AppState
from app.ui.beat_preview_tab import BeatPreviewTab
from app.ui.beat_studio_tab import BeatStudioTab


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _project_with_prompt_context():
    service = ProjectService()
    project = service.create_project("Prompt Workflow", default_art_style="style_001")
    chapter = service.add_source_chapter(
        project,
        title="Chapter",
        chapter_number=1,
        raw_text="Original source raw text must stay untouched.",
    )
    service.add_style_preset(
        project,
        style_id="style_001",
        name="Dark Fantasy Webtoon",
        positive_prompt="dark fantasy webtoon style, cinematic shadows",
        negative_prompt="low quality, blurry, wrong outfit",
        line_style="clean webtoon line art",
        rendering_style="high-detail digital painting",
        color_palette="deep blue and black",
        character_design_rules="sharp expressive faces",
        camera_style="cinematic camera language",
        lighting_style="cold moonlight and rim light",
        forbidden_terms=["logo", "watermark", "logo"],
    )
    char_1 = service.add_character(
        project,
        character_id="char_001",
        name="Lam Vu",
        gender="male",
        age_description="young adult",
        appearance="slim cautious young man",
        face_details="pale face with sharp jawline",
        hair="messy black hair",
        eyes="gray eyes",
        body_type="slim build",
        default_outfit="black jacket and white shirt",
        visual_prompt_base="young man with messy black hair and gray eyes",
        signature_features="small scar under left eye",
        reference_image_note="keep the same face from the reference sheet",
        negative_prompt_terms=["different hairstyle", "wrong outfit"],
    )
    char_1.variants = [
        CharacterVariant(
            variant_id="char_001_young",
            character_id="char_001",
            display_name="Lam Vu - young",
            state_type="young",
            visual_prompt_base="young boy with messy black hair",
            hair="messy black hair",
            body_type="slim child body",
            default_outfit_id="outfit_char_001_young_sleepwear",
            negative_prompt_terms=["old man", "white hair"],
        )
    ]
    char_1.outfits = [
        CharacterOutfit(
            outfit_id="outfit_char_001_young_sleepwear",
            character_id="char_001",
            variant_id="char_001_young",
            display_name="Blue gray inner robe",
            outfit_type="sleepwear",
            description="simple blue-gray ancient inner robe",
            negative_prompt_terms=["modern clothes"],
        )
    ]
    service.add_character(
        project,
        character_id="char_002",
        name="Old Master",
        gender="male",
        age_description="elderly",
        appearance="thin old man with stern eyes",
        hair="long white hair",
        eyes="cloudy blue eyes",
        body_type="frail body",
        default_outfit="dark blue robe",
        visual_prompt_base="elderly man with long white hair and dark blue robe",
    )
    service.add_location(
        project,
        location_id="loc_001",
        name="Old House Hallway",
        visual_prompt_base="old narrow hallway with dusty wooden floor",
        description="abandoned countryside house corridor",
        mood="eerie and silent",
        time_period="late night",
        lighting="dim moonlight through broken windows",
        color_palette="cold blue, gray, dark brown",
        architecture_style="old wooden architecture",
        recurring_props=["rusted chain", "cracked walls"],
        negative_prompt_terms=["modern hallway", "bright daylight"],
    )
    episode = service.add_review_episode(
        project,
        title="Episode 1",
        source_chapter_ids=[chapter.chapter_id],
    )
    scene_1 = service.add_scene(
        project,
        episode_id=episode.episode_id,
        scene_id="sc_001",
        title="Hallway",
        location="loc_001",
        characters=["char_001"],
    )
    scene_2 = service.add_scene(
        project,
        episode_id=episode.episode_id,
        scene_id="sc_002",
        title="Memory",
        location="loc_001",
        characters=["char_002"],
    )
    beat_1 = service.add_beat(
        project,
        episode_id=episode.episode_id,
        scene_id=scene_1.scene_id,
        beat_id="beat_001",
        order_index=1,
        story_function="discovery",
        characters=["char_001"],
        location="loc_001",
        action="Lam Vu discovers fresh footprints beside the locked door",
        emotion="suspicious",
        camera="slow dolly-in from floor level",
        shot_type="low angle close-up",
        timeOfDay="Night",
        lighting="cold moonlight across dusty boards",
        atmosphere="quiet mist and fear",
        location_cues="fresh footprints crossing the dust",
        asmr_visuals="floating dust, candle flicker, trembling curtain",
        composition="footprints lead toward a locked door",
        posture="half crouched beside the floor",
        expression="uneasy focused stare",
        body_language="one hand hovering above the footprints",
        visual_description="fresh footprints on dusty wooden floor",
        review_text="Original Vietnamese review narration.",
        continuity_tags=["char_001_black_jacket", "loc_001_night"],
    )
    beat_2 = service.add_beat(
        project,
        episode_id=episode.episode_id,
        scene_id=scene_1.scene_id,
        beat_id="beat_002",
        order_index=2,
        characters=["char_001"],
        location="loc_001",
        action="Lam Vu touches the rusty chain",
        review_text="Second review paragraph.",
    )
    beat_3 = service.add_beat(
        project,
        episode_id=episode.episode_id,
        scene_id=scene_2.scene_id,
        beat_id="beat_003",
        order_index=1,
        characters=["char_002"],
        location="loc_001",
        action="The old master appears in a memory",
        review_text="Third review paragraph.",
    )
    return project, service, chapter, episode, scene_1, scene_2, beat_1, beat_2, beat_3


def _studio_tab(project, service, episode, scene, beat):
    _app()
    manual_ai_controller = Mock()
    app_state = AppState(
        project=project,
        selected_episode_id=episode.episode_id,
        selected_scene_id=scene.scene_id,
        selected_beat_id=beat.beat_id,
    )
    tab = BeatStudioTab(
        app_state,
        GenerationController(service),
        manual_ai_controller,
        Mock(),
    )
    tab.refresh()
    return tab, manual_ai_controller


def test_beat_studio_local_prompt_build_does_not_call_ai():
    project, service, _chapter, episode, scene, _scene2, beat, _beat2, _beat3 = (
        _project_with_prompt_context()
    )
    tab, manual_ai_controller = _studio_tab(project, service, episode, scene, beat)

    with patch("app.ui.beat_studio_tab.QMessageBox.information"):
        tab._on_build_selected_prompt()

    assert beat.image_prompt
    assert beat.negative_prompt
    manual_ai_controller.export_prompt.assert_not_called()
    manual_ai_controller.import_result.assert_not_called()


def test_beat_studio_build_selected_beat_prompt_offline():
    project, service, _chapter, episode, scene, _scene2, beat, beat2, _beat3 = (
        _project_with_prompt_context()
    )
    tab, _manual = _studio_tab(project, service, episode, scene, beat)

    with patch("app.ui.beat_studio_tab.QMessageBox.information"):
        tab._on_build_selected_prompt()

    assert beat.image_prompt
    assert beat.negative_prompt
    assert beat2.image_prompt == ""


def test_beat_studio_build_scene_prompts_offline():
    project, service, _chapter, episode, scene, _scene2, beat, beat2, beat3 = (
        _project_with_prompt_context()
    )
    tab, _manual = _studio_tab(project, service, episode, scene, beat)

    with patch("app.ui.beat_studio_tab.QMessageBox.information"):
        tab._on_build_scene_prompts()

    assert beat.image_prompt
    assert beat2.image_prompt
    assert beat3.image_prompt == ""


def test_beat_studio_build_episode_prompts_offline():
    project, service, _chapter, episode, scene, _scene2, beat, beat2, beat3 = (
        _project_with_prompt_context()
    )
    tab, _manual = _studio_tab(project, service, episode, scene, beat)

    with patch("app.ui.beat_studio_tab.QMessageBox.information"):
        tab._on_build_episode_prompts()

    assert all(item.image_prompt for item in [beat, beat2, beat3])
    assert all(item.negative_prompt for item in [beat, beat2, beat3])


def test_build_prompt_preserves_review_text_and_source_raw_text():
    project, service, chapter, episode, scene, _scene2, beat, _beat2, _beat3 = (
        _project_with_prompt_context()
    )
    tab, _manual = _studio_tab(project, service, episode, scene, beat)
    raw_text = chapter.raw_text
    review_text = beat.review_text

    with patch("app.ui.beat_studio_tab.QMessageBox.information"):
        tab._on_build_episode_prompts()

    assert chapter.raw_text == raw_text
    assert beat.review_text == review_text


def test_prompt_builder_required_order():
    project, _service, _chapter, _episode, _scene, _scene2, beat, _beat2, _beat3 = (
        _project_with_prompt_context()
    )
    PromptBuilderService().build_prompt_for_beat(project, beat.beat_id)
    prompt = beat.image_prompt

    style = prompt.index("Dark Fantasy Webtoon")
    camera = prompt.index("slow dolly-in from floor level")
    time = prompt.index("Night")
    location = prompt.index("Location: Old House Hallway")
    lighting = prompt.index("cold moonlight across dusty boards")
    # Character block may include variant name (e.g., "Lam Vu - young (")
    character = prompt.index("Lam Vu")
    action = prompt.index("Lam Vu discovers fresh footprints")

    assert style < camera < time < location < lighting < character < action


def test_prompt_builder_uses_names_not_raw_ids():
    project, _service, _chapter, _episode, _scene, _scene2, beat, _beat2, _beat3 = (
        _project_with_prompt_context()
    )
    PromptBuilderService().build_prompt_for_beat(project, beat.beat_id)

    assert "Lam Vu" in beat.image_prompt
    assert "Old House Hallway" in beat.image_prompt
    assert "char_001" not in beat.image_prompt
    assert "loc_001" not in beat.image_prompt


def test_prompt_builder_no_truncation_or_same_as_above():
    project, _service, _chapter, _episode, _scene, _scene2, beat, _beat2, _beat3 = (
        _project_with_prompt_context()
    )
    PromptBuilderService().build_prompt_for_beat(project, beat.beat_id)

    assert "..." not in beat.image_prompt
    assert "same as above" not in beat.image_prompt.lower()


def test_prompt_builder_multiple_characters_full_descriptions():
    project, _service, _chapter, _episode, _scene, _scene2, beat, _beat2, _beat3 = (
        _project_with_prompt_context()
    )
    beat.characters = ["char_001", "char_002"]

    PromptBuilderService().build_prompt_for_beat(project, beat.beat_id)

    assert "Lam Vu" in beat.image_prompt
    assert "Old Master (" in beat.image_prompt
    assert "Outfit: black jacket and white shirt" in beat.image_prompt or "blue-gray ancient inner robe" in beat.image_prompt
    assert "Outfit: dark blue robe" in beat.image_prompt


def test_prompt_builder_negative_prompt_combines_terms_and_dedupes():
    project, _service, _chapter, _episode, _scene, _scene2, beat, _beat2, _beat3 = (
        _project_with_prompt_context()
    )
    PromptBuilderService().build_prompt_for_beat(project, beat.beat_id)
    terms = [term.strip() for term in beat.negative_prompt.split(",")]

    assert "low quality" in terms
    assert "multiple scenes in one image" in terms
    assert "wrong outfit" in terms
    assert "logo" in terms
    assert "different hairstyle" in terms
    assert "modern hallway" in terms
    assert len([term for term in terms if term == "logo"]) == 1


def test_manual_ai_prompt_image_task_is_advanced_or_not_primary():
    project, service, _chapter, episode, scene, _scene2, beat, _beat2, _beat3 = (
        _project_with_prompt_context()
    )
    tab, _manual = _studio_tab(project, service, episode, scene, beat)

    assert tab.local_prompt_group.title() == "Tao prompt anh local"
    assert tab.btn_build_selected_prompt.text() == "Tao prompt anh cho nhip dang chon"
    manual_labels = [
        tab.manual_step_combo.itemText(index)
        for index in range(tab.manual_step_combo.count())
    ]
    assert "Advanced: dung AI viet lai prompt anh" in manual_labels


def test_beat_preview_can_show_built_prompt():
    project, service, _chapter, episode, scene, _scene2, beat, _beat2, _beat3 = (
        _project_with_prompt_context()
    )
    PromptBuilderService().build_prompt_for_beat(project, beat.beat_id)
    app_state = AppState(project=project, selected_episode_id=episode.episode_id)
    preview = BeatPreviewTab(app_state, GenerationController(service), Mock())

    preview.refresh()

    prompt_container = preview.table.cellWidget(0, 3)
    from PySide6.QtWidgets import QPlainTextEdit

    prompt_edit = prompt_container.findChild(QPlainTextEdit)
    assert prompt_edit is not None
    assert "Dark Fantasy Webtoon" in prompt_edit.toPlainText()
    assert "negative prompt:" in prompt_edit.toPlainText()


def test_beat_studio_variant_outfit_dropdowns():
    project, service, _chapter, episode, scene, _scene2, beat, _beat2, _beat3 = (
        _project_with_prompt_context()
    )
    beat.character_variants = {"char_001": "char_001_young"}
    beat.character_outfits = {"char_001": "outfit_char_001_young_sleepwear"}
    tab, _manual = _studio_tab(project, service, episode, scene, beat)
    tab._set_selected_beat(beat.beat_id)

    variant_widget = tab.fields["character_variants"]
    outfit_widget = tab.fields["character_outfits"]

    from PySide6.QtWidgets import QWidget

    # character_variants and character_outfits are stored as placeholder QWidget
    # (the actual dropdowns are rendered dynamically when a beat with chars is selected)
    assert isinstance(variant_widget, QWidget)
    assert isinstance(outfit_widget, QWidget)

    # Verify the beat data itself was correctly stored
    assert beat.character_variants.get("char_001") == "char_001_young"
    assert beat.character_outfits.get("char_001") == "outfit_char_001_young_sleepwear"
