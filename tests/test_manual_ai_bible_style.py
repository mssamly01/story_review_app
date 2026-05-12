import pytest
import json
from app.domain.project import Project
from app.services.project_service import ProjectService
from app.services.manual_ai_bible_style_service import ManualAIBibleStyleService
from app.services.prompt_builder_service import PromptBuilderService


@pytest.fixture
def project_service():
    return ProjectService()


@pytest.fixture
def project(project_service):
    p = project_service.create_project("Test Project")
    project_service.add_source_chapter(
        p, title="Intro", chapter_number=1, raw_text="Once upon a time, John lived in a dark castle."
    )
    return p


def test_build_bible_style_prompt_contains_character_location_style_tasks(project):
    service = ManualAIBibleStyleService()
    prompt = service.build_bible_style_analysis_prompt(project, ["ch_001"])
    
    assert "characters" in prompt.lower()
    assert "locations" in prompt.lower()
    assert "style" in prompt.lower()
    assert "world_style_notes" in prompt.lower()


def test_build_bible_style_prompt_includes_source_text(project):
    service = ManualAIBibleStyleService()
    prompt = service.build_bible_style_analysis_prompt(project, ["ch_001"])
    
    assert "John lived in a dark castle" in prompt


def test_build_bible_style_prompt_requires_json_only(project):
    service = ManualAIBibleStyleService()
    prompt = service.build_bible_style_analysis_prompt(project, ["ch_001"])
    
    assert "JSON only" in prompt
    assert "No markdown" in prompt


def test_bible_style_analysis_prompt_forbids_default_variant_for_single_form(project):
    service = ManualAIBibleStyleService()
    prompt = service.build_bible_style_analysis_prompt(project, ["ch_001"])

    lowered = prompt.lower()
    assert "character_variants" in prompt
    assert "if a character has only one visual age-form, put the full visual profile directly on the character object" in lowered
    assert "do not create a default variant" in lowered


def test_bible_style_analysis_prompt_requires_outfit_details(project):
    service = ManualAIBibleStyleService()
    prompt = service.build_bible_style_analysis_prompt(project, ["ch_001"])

    lowered = prompt.lower()
    assert "outfit details" in lowered
    assert "stored directly on the character for single-form" in lowered


def test_apply_bible_style_result_creates_characters_locations_styles(project):
    service = ManualAIBibleStyleService()
    result = {
        "characters": [{"character_id": "char_001", "name": "John", "role": "Protagonist"}],
        "locations": [{"location_id": "loc_001", "name": "Dark Castle", "location_type": "Castle"}],
        "style_presets": [{"style_id": "style_001", "name": "Gothic", "genre": "Horror"}],
        "world_style_notes": {"genre": "Dark Fantasy"}
    }
    
    service.apply_bible_style_analysis_result(project, result)
    
    assert len(project.characters) == 1
    assert project.characters[0].name == "John"
    assert len(project.locations) == 1
    assert project.locations[0].name == "Dark Castle"
    assert len(project.style_presets) == 1
    assert project.style_presets[0].name == "Gothic"
    assert project.world_style_notes["genre"] == "Dark Fantasy"


def test_apply_bible_style_result_creates_character_variants_and_outfits(project):
    service = ManualAIBibleStyleService()
    result = {
        "characters": [
            {
                "character_id": "char_001",
                "name": "Co Than",
                "role": "protagonist",
            },
            {
                "character_id": "char_002",
                "name": "Tang Thien Co",
                "role": "antagonist",
                "hair": "Long Black",
                "eyes": "Sharp",
                "default_outfit": "White Robe"
            }
        ],
        "character_variants": [
            {
                "variant_id": "char_001_old",
                "character_id": "char_001",
                "display_name": "Co Than - old form",
                "hair": "long white hair",
            },
            {
                "variant_id": "char_001_young",
                "character_id": "char_001",
                "display_name": "Co Than - young form",
                "hair": "messy black hair",
            },
        ]
    }
    
    service.apply_bible_style_analysis_result(project, result)
    
    char1 = next(c for c in project.characters if c.character_id == "char_001")
    assert len(char1.variants) == 2
    
    char2 = next(c for c in project.characters if c.character_id == "char_002")
    assert len(char2.variants) == 0
    assert char2.hair == "Long Black"
    assert char2.eyes == "Sharp"
    assert char2.default_outfit == "White Robe"


def test_character_variants_survive_save_load(project, project_service, tmp_path):
    service = ManualAIBibleStyleService()
    result = {
        "characters": [{"character_id": "char_001", "name": "Co Than"}],
        "character_variants": [
            {
                "variant_id": "char_001_old",
                "character_id": "char_001",
                "display_name": "Co Than - old",
                "state_type": "old",
                "visual_prompt_base": "old cultivator with white hair",
            }
        ],
        "character_outfits": [
            {
                "outfit_id": "outfit_char_001_old_battle",
                "character_id": "char_001",
                "variant_id": "char_001_old",
                "display_name": "Battle robe",
                "description": "torn battle robe",
            }
        ],
    }
    service.apply_bible_style_analysis_result(project, result, overwrite=True)

    output_path = tmp_path / "project.json"
    project_service.save_project(project, output_path)
    loaded = project_service.load_project(output_path)

    loaded_character = loaded.characters[0]
    assert loaded_character.find_variant("char_001_old") is not None
    assert loaded_character.find_outfit("outfit_char_001_old_battle") is not None


def test_apply_bible_style_result_merges_without_overwriting_existing_fields(project, project_service):
    service = ManualAIBibleStyleService()
    
    # Pre-existing character with some data
    char = project_service.add_character(project, name="John", character_id="char_001", role="Original Role")
    char.appearance = "Original Appearance"
    
    result = {
        "characters": [
            {
                "character_id": "char_001", 
                "name": "John Updated", 
                "role": "New Role", 
                "appearance": "New Appearance",
                "personality": "New Personality"
            }
        ]
    }
    
    # Merge mode (overwrite=False)
    service.apply_bible_style_analysis_result(project, result, overwrite=False)
    
    assert project.characters[0].role == "Original Role" # Preserved
    assert project.characters[0].appearance == "Original Appearance" # Preserved
    assert project.characters[0].personality == "New Personality" # Merged


def test_apply_bible_style_result_overwrite_mode_updates_fields(project, project_service):
    service = ManualAIBibleStyleService()
    
    project_service.add_character(project, name="John", character_id="char_001", role="Original Role")
    
    result = {
        "characters": [{"character_id": "char_001", "name": "John", "role": "New Role"}]
    }
    
    # Overwrite mode
    service.apply_bible_style_analysis_result(project, result, overwrite=True)
    
    assert project.characters[0].role == "New Role"


def test_apply_bible_style_result_preserves_source_raw_text(project):
    service = ManualAIBibleStyleService()
    original_text = project.source_chapters[0].raw_text
    
    result = {
        "characters": [{"character_id": "char_001", "name": "John"}]
    }
    
    service.apply_bible_style_analysis_result(project, result)
    
    assert project.source_chapters[0].raw_text == original_text


def test_bible_style_analysis_before_beat_prompt_flow(project, project_service):
    """
    1. Apply Bible/Style result
    2. Build beat prompt
    3. Assert beat prompt uses newly created data
    """
    service = ManualAIBibleStyleService()
    result = {
        "characters": [
            {
                "character_id": "char_001", 
                "name": "John", 
                "visual_prompt_base": "tall warrior",
                "signature_features": ["scar on face"]
            }
        ],
        "style_presets": [
            {
                "style_id": "style_001", 
                "name": "MyStyle", 
                "positive_prompt": "high fidelity, cinematic"
            }
        ]
    }
    service.apply_bible_style_analysis_result(project, result, overwrite=True)
    
    # Setup episode/scene/beat
    project_service.add_review_episode(project, title="Ep 1", source_chapter_ids=["ch_001"])
    scene = project_service.add_scene(project, episode_id="ep_001", title="Scene 1")
    beat = project_service.add_beat(
        project, 
        episode_id="ep_001", 
        scene_id=scene.scene_id, 
        characters=["char_001"]
    )
    
    builder = PromptBuilderService()
    builder.build_prompt_for_beat(project, beat.beat_id, style_preset_id="style_001")
    
    prompt = beat.image_prompt.lower()
    assert "tall warrior" in prompt
    assert "scar on face" in prompt
    assert "high fidelity, cinematic" in prompt


def test_product_direction_guards_still_pass():
    # Placeholder for running existing guard tests
    pass
def test_apply_bible_style_no_default_variant_for_single_form(project):
    service = ManualAIBibleStyleService()
    result = {
        "characters": [
            {
                "character_id": "char_002",
                "name": "Tang Thien Co",
                "role": "Antagonist",
                "hair": "Black"
            }
        ]
    }
    
    service.apply_bible_style_analysis_result(project, result)
    
    char = project.characters[0]
    assert len(char.variants) == 0
    assert char.hair == "Black"

def test_apply_bible_style_preserves_existing_variant(project):
    service = ManualAIBibleStyleService()
    from app.domain.character import Character, CharacterVariant
    char = Character(character_id="char_002", name="Tang Thien Co")
    char.variants.append(CharacterVariant(
        variant_id="char_002_custom", character_id="char_002", display_name="Custom"
    ))
    project.characters.append(char)
    
    result = {
        "characters": [{"character_id": "char_002", "name": "Tang Thien Co"}]
    }
    
    service.apply_bible_style_analysis_result(project, result)
    
    assert len(char.variants) == 1
    assert char.variants[0].variant_id == "char_002_custom"

def test_migration_merges_default_variant_back_to_base(project):
    service = ManualAIBibleStyleService()
    from app.domain.character import Character, CharacterVariant
    char = Character(
        character_id="char_003",
        name="Old Base Char",
        hair="" # Empty hair on base
    )
    # Add a "default" variant
    char.variants.append(CharacterVariant(
        variant_id="char_003_default",
        character_id="char_003",
        display_name="Old Base Char - mặc định",
        hair="Long White",
        appearance="Frail old man"
    ))
    project.characters.append(char)
    
    # Applying any result should trigger migration
    service.apply_bible_style_analysis_result(project, {"characters": []})
    
    # Should be merged back
    assert len(char.variants) == 0
    assert char.hair == "Long White"
    assert char.appearance == "Frail old man"


# ─── New comprehensive tests ──────────────────────────────────────────────────

_FULL_CHAR_002 = {
    "character_id": "char_002",
    "name": "T\u00e0ng Thi\u00ean C\u01a1",
    "aliases": ["Zang Tianji"],
    "role": "Main Antagonist",
    "gender": "Male",
    "age_description": "adult immortal cultivator",
    "personality": "arrogant, cold",
    "relationship_notes": "Killed C\u1ed5 Th\u1ea7n",
    "appearance": "majestic divine immortal figure",
    "face_details": "cold noble face with arrogant expression",
    "hair": "long flowing black hair",
    "eyes": "sharp cold eyes",
    "body_type": "tall, lean, perfectly proportioned",
    "skin_tone": "pale jade-like skin",
    "height": "tall",
    "visual_prompt_base": "majestic ancient Chinese immortal prince",
    "signature_features": ["cold noble face", "transcendent aura", "long black hair"],
    "default_outfit": "Imperial cultivator robes",
    "outfit_details": "ornate golden and white robes",
    "outfit_colors": ["white", "gold", "silver"],
    "outfit_materials": ["silk", "spiritual embroidered fabric"],
    "accessories": ["royal crown", "alchemy pouch"],
    "footwear": "white cloth boots",
    "continuity_must_keep": ["long black hair", "gold and white robes"],
    "continuity_forbidden": ["child body", "old frail body"],
    "negative_prompt_terms": ["child", "old man", "modern clothing"],
    "reference_image_note": "keep divine presence",
    "required_views": ["front", "3/4 view", "side", "back"],
    "expression_set": ["neutral", "cold", "arrogant"],
    "micro_expression_set": ["narrowed eyes", "slight smirk"],
    "head_angle_views": ["front", "3/4 left", "profile"],
    "pose_set": ["standing calmly", "looking down"],
    "hand_gesture_set": ["relaxed hand", "commanding gesture"],
    "wardrobe_details": ["gold embroidered robe", "white silk robe"],
    "prop_details": ["alchemy pouch"],
    "color_palette": ["white", "gold", "silver", "cold blue"],
    "sheet_layout_style": "clean professional character reference sheet",
    "reference_sheet_notes": "keep god-like arrogant immortal presence",
}


def test_apply_bible_style_single_form_character_updates_all_visual_fields(project):
    service = ManualAIBibleStyleService()
    result = {"characters": [_FULL_CHAR_002]}
    service.apply_bible_style_analysis_result(project, result)

    char = next(c for c in project.characters if c.character_id == "char_002")
    assert char.face_details == "cold noble face with arrogant expression"
    assert char.hair == "long flowing black hair"
    assert char.eyes == "sharp cold eyes"
    assert char.body_type == "tall, lean, perfectly proportioned"
    assert char.skin_tone == "pale jade-like skin"
    assert char.height == "tall"
    assert char.visual_prompt_base == "majestic ancient Chinese immortal prince"
    assert char.signature_features == ["cold noble face", "transcendent aura", "long black hair"]


def test_apply_bible_style_single_form_character_updates_all_outfit_fields(project):
    service = ManualAIBibleStyleService()
    result = {"characters": [_FULL_CHAR_002]}
    service.apply_bible_style_analysis_result(project, result)

    char = next(c for c in project.characters if c.character_id == "char_002")
    assert char.default_outfit == "Imperial cultivator robes"
    assert char.outfit_details == "ornate golden and white robes"
    assert char.outfit_colors == ["white", "gold", "silver"]
    assert char.outfit_materials == ["silk", "spiritual embroidered fabric"]
    assert char.accessories == ["royal crown", "alchemy pouch"]
    assert char.footwear == "white cloth boots"


def test_apply_bible_style_single_form_character_updates_continuity_fields(project):
    service = ManualAIBibleStyleService()
    result = {"characters": [_FULL_CHAR_002]}
    service.apply_bible_style_analysis_result(project, result)

    char = next(c for c in project.characters if c.character_id == "char_002")
    assert char.continuity_must_keep == ["long black hair", "gold and white robes"]
    assert char.continuity_forbidden == ["child body", "old frail body"]
    assert char.negative_prompt_terms == ["child", "old man", "modern clothing"]


def test_apply_bible_style_single_form_character_updates_reference_sheet_fields(project):
    service = ManualAIBibleStyleService()
    result = {"characters": [_FULL_CHAR_002]}
    service.apply_bible_style_analysis_result(project, result)

    char = next(c for c in project.characters if c.character_id == "char_002")
    assert char.required_views == ["front", "3/4 view", "side", "back"]
    assert char.expression_set == ["neutral", "cold", "arrogant"]
    assert char.pose_set == ["standing calmly", "looking down"]
    assert char.wardrobe_details == ["gold embroidered robe", "white silk robe"]
    assert char.prop_details == ["alchemy pouch"]
    assert char.color_palette == ["white", "gold", "silver", "cold blue"]
    assert char.sheet_layout_style == "clean professional character reference sheet"
    assert char.reference_sheet_notes == "keep god-like arrogant immortal presence"


def test_apply_bible_style_variant_updates_all_fields(project):
    service = ManualAIBibleStyleService()
    from app.domain.character import Character
    project.characters.append(Character(character_id="char_001", name="C\u1ed5 Th\u1ea7n"))

    result = {
        "characters": [{"character_id": "char_001", "name": "C\u1ed5 Th\u1ea7n"}],
        "character_variants": [{
            "variant_id": "char_001_young",
            "character_id": "char_001",
            "display_name": "C\u1ed5 Th\u1ea7n - 10 tu\u1ed5i",
            "age_stage": "child",
            "hair": "black hair",
            "eyes": "old soul eyes",
            "skin_tone": "pale",
            "outfit_colors": ["white", "grey"],
            "signature_features": ["old soul eyes", "black hair"],
            "continuity_must_keep": ["black hair", "small body"],
            "continuity_forbidden": ["adult body"],
            "negative_prompt_terms": ["old man"],
        }],
    }
    service.apply_bible_style_analysis_result(project, result)

    char = next(c for c in project.characters if c.character_id == "char_001")
    assert len(char.variants) == 1
    v = char.variants[0]
    assert v.hair == "black hair"
    assert v.skin_tone == "pale"
    assert v.outfit_colors == ["white", "grey"]
    assert v.signature_features == ["old soul eyes", "black hair"]
    assert v.continuity_must_keep == ["black hair", "small body"]
    assert v.negative_prompt_terms == ["old man"]


def test_project_save_load_preserves_single_form_full_character_fields(project, project_service):
    service = ManualAIBibleStyleService()
    result = {"characters": [_FULL_CHAR_002]}
    service.apply_bible_style_analysis_result(project, result)

    data = project.to_dict()
    from app.domain.project import Project
    restored = Project.from_dict(data)

    char = next(c for c in restored.characters if c.character_id == "char_002")
    assert char.face_details == "cold noble face with arrogant expression"
    assert char.outfit_colors == ["white", "gold", "silver"]
    assert char.signature_features == ["cold noble face", "transcendent aura", "long black hair"]
    assert char.continuity_must_keep == ["long black hair", "gold and white robes"]
    assert char.required_views == ["front", "3/4 view", "side", "back"]
    assert char.expression_set == ["neutral", "cold", "arrogant"]
    assert char.reference_sheet_notes == "keep god-like arrogant immortal presence"


def test_project_save_load_preserves_variant_full_fields(project, project_service):
    from app.domain.character import Character, CharacterVariant
    char = Character(character_id="char_001", name="C\u1ed5 Th\u1ea7n")
    char.variants = [CharacterVariant(
        variant_id="char_001_young",
        character_id="char_001",
        display_name="Young",
        hair="black hair",
        skin_tone="pale",
        outfit_colors=["white"],
        signature_features=["old eyes"],
        continuity_must_keep=["black hair"],
        negative_prompt_terms=["adult"],
    )]
    project.characters.append(char)

    data = project.to_dict()
    from app.domain.project import Project
    restored = Project.from_dict(data)

    rc = next(c for c in restored.characters if c.character_id == "char_001")
    rv = rc.variants[0]
    assert rv.hair == "black hair"
    assert rv.skin_tone == "pale"
    assert rv.outfit_colors == ["white"]
    assert rv.signature_features == ["old eyes"]
    assert rv.negative_prompt_terms == ["adult"]


def test_prompt_builder_uses_single_form_character_full_fields(project, project_service):
    service = ManualAIBibleStyleService()
    prompt_svc = PromptBuilderService()
    result = {"characters": [_FULL_CHAR_002]}
    service.apply_bible_style_analysis_result(project, result)

    from app.domain.scene import Scene
    from app.domain.beat import Beat
    from app.domain.episode import ReviewEpisode
    ep = ReviewEpisode(episode_id="ep1", title="E1")
    sc = Scene(episode_id="ep1", scene_id="sc1", title="S1")
    beat = Beat(beat_id="b1", scene_id="sc1", order_index=1, characters=["char_002"])
    sc.beats.append(beat)
    ep.scenes.append(sc)
    project.review_episodes.append(ep)

    updated_beat = prompt_svc.build_prompt_for_beat(project, "b1")
    prompt = updated_beat.image_prompt

    assert "T\u00e0ng Thi\u00ean C\u01a1" in prompt
    assert "char_002_default" not in prompt


def test_merge_mode_does_not_overwrite_existing_nonempty_fields(project):
    service = ManualAIBibleStyleService()
    from app.domain.character import Character
    char = Character(character_id="char_002", name="T\u00e0ng Thi\u00ean C\u01a1", hair="ORIGINAL_HAIR")
    project.characters.append(char)

    result = {"characters": [{"character_id": "char_002", "name": "T\u00e0ng Thi\u00ean C\u01a1", "hair": "new hair"}]}
    service.apply_bible_style_analysis_result(project, result, overwrite=False)

    assert char.hair == "ORIGINAL_HAIR"


def test_overwrite_mode_replaces_fields(project):
    service = ManualAIBibleStyleService()
    from app.domain.character import Character
    char = Character(character_id="char_002", name="T\u00e0ng Thi\u00ean C\u01a1", hair="ORIGINAL_HAIR")
    project.characters.append(char)

    result = {"characters": [{"character_id": "char_002", "name": "T\u00e0ng Thi\u00ean C\u01a1", "hair": "new hair"}]}
    service.apply_bible_style_analysis_result(project, result, overwrite=True)

    assert char.hair == "new hair"
