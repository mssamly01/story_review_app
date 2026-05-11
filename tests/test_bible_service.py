from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.domain.character import Character
from app.domain.location import Location
from app.domain.style_preset import StylePreset
from app.services.bible_service import BibleService
from app.services.project_service import ProjectService


class BibleServiceTests(unittest.TestCase):
    def test_character_bible_supports_advanced_fields(self) -> None:
        project_service = ProjectService()
        project = project_service.create_project("Bible Story")
        character = Character(
            character_id="lam_vu",
            name="Lam Vu",
            aliases=["Vu"],
            role="lead",
            gender="male",
            age_description="young adult",
            appearance="slim build",
            face_details="sharp jawline",
            hair="messy black hair",
            eyes="gray eyes",
            body_type="lean",
            default_outfit="black jacket, white shirt",
            outfit_variants=["raincoat"],
            visual_prompt_base="young man with messy black hair and gray eyes",
            negative_prompt_terms=["wrong hair color"],
            continuity_tags=["lam_vu_black_jacket"],
        )
        BibleService().add_or_update_character(project, character)

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.json"
            project_service.save_project(project, path)
            loaded = project_service.load_project(path)

        loaded_character = loaded.characters[0]
        self.assertEqual(loaded_character.hair, "messy black hair")
        self.assertEqual(loaded_character.eyes, "gray eyes")
        self.assertEqual(loaded_character.default_outfit, "black jacket, white shirt")
        self.assertEqual(loaded_character.negative_prompt_terms, ["wrong hair color"])

    def test_location_bible_supports_advanced_fields(self) -> None:
        project_service = ProjectService()
        project = project_service.create_project("Bible Story")
        location = Location(
            location_id="old_house",
            name="Old House",
            aliases=["grandfather house"],
            location_type="countryside house",
            description="abandoned family home",
            mood="mysterious",
            time_period="night",
            lighting="moonlit windows",
            color_palette="cold blue and dusty brown",
            architecture_style="old wooden architecture",
            recurring_props=["locked door", "dusty portrait"],
            visual_prompt_base="old countryside house, dusty rooms",
            negative_prompt_terms=["modern furniture"],
            continuity_tags=["old_house_night"],
        )
        BibleService().add_or_update_location(project, location)

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.json"
            project_service.save_project(project, path)
            loaded = project_service.load_project(path)

        loaded_location = loaded.locations[0]
        self.assertEqual(loaded_location.aliases, ["grandfather house"])
        self.assertEqual(loaded_location.lighting, "moonlit windows")
        self.assertEqual(loaded_location.recurring_props, ["locked door", "dusty portrait"])
        self.assertEqual(loaded_location.negative_prompt_terms, ["modern furniture"])

    def test_style_preset_supports_advanced_fields(self) -> None:
        project_service = ProjectService()
        project = project_service.create_project("Bible Story")
        style = StylePreset(
            style_id="noir",
            name="Noir",
            positive_prompt="noir detective comic style",
            negative_prompt="low contrast",
            genre="mystery",
            line_style="bold ink lines",
            color_palette="black, gray, amber",
            lighting_style="streetlamp glow",
            rendering_style="graphic comic rendering",
            background_detail_level="high",
            camera_style="dramatic close-ups",
            mood_keywords=["suspicious"],
            forbidden_terms=["text", "watermark"],
        )
        BibleService().add_or_update_style_preset(project, style)

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.json"
            project_service.save_project(project, path)
            loaded = project_service.load_project(path)

        loaded_style = loaded.style_presets[0]
        self.assertEqual(loaded_style.positive_prompt, "noir detective comic style")
        self.assertEqual(loaded_style.lighting_style, "streetlamp glow")
        self.assertEqual(loaded_style.color_palette, "black, gray, amber")
        self.assertEqual(loaded_style.forbidden_terms, ["text", "watermark"])

    def test_bible_service_add_or_update_character_idempotent(self) -> None:
        project = ProjectService().create_project("Bible Story")
        service = BibleService()

        service.add_or_update_character(
            project,
            Character(character_id="lan", name="Lan", appearance="short hair"),
        )
        service.add_or_update_character(
            project,
            Character(character_id="lan", name="Lan", appearance="long hair"),
        )

        self.assertEqual(len(project.characters), 1)
        self.assertEqual(project.characters[0].appearance, "long hair")

    def test_bible_service_find_character_by_alias(self) -> None:
        project = ProjectService().create_project("Bible Story")
        service = BibleService()
        service.add_or_update_character(
            project,
            Character(character_id="lan", name="Lan", aliases=["detective girl"]),
        )

        found = service.find_character_by_name_or_alias(project, "Detective Girl")

        self.assertIsNotNone(found)
        self.assertEqual(found.character_id, "lan")

    def test_bible_service_create_default_style_presets(self) -> None:
        project = ProjectService().create_project("Bible Story")

        presets = BibleService().create_default_style_presets(project)

        preset_ids = {preset.style_id for preset in presets}
        self.assertIn("dark_fantasy_webtoon", preset_ids)
        self.assertIn("soft_watercolor_webtoon", preset_ids)
        self.assertEqual(len(project.style_presets), len(presets))
        self.assertTrue(all(preset.positive_prompt for preset in presets))
        self.assertTrue(all(preset.negative_prompt for preset in presets))


if __name__ == "__main__":
    unittest.main()
