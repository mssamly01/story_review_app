"""Tests for Character bible visual-reference fields.

These fields are metadata for downstream image renderers and have NO behavior
attached inside the app. We just want to ensure they survive a JSON round trip
and that the on-disk schema is stable.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.domain.character import Character
from app.services.project_service import ProjectService


class CharacterReferenceFieldTests(unittest.TestCase):
    def test_character_defaults_have_empty_reference_fields(self) -> None:
        char = Character(character_id="c1", name="Test")
        self.assertEqual(char.reference_image_paths, [])
        self.assertEqual(char.sd_lora_name, "")
        self.assertEqual(char.ip_adapter_image_path, "")
        self.assertEqual(char.character_embedding_hash, "")

    def test_character_to_dict_includes_reference_fields(self) -> None:
        char = Character(
            character_id="c1",
            name="Hero",
            reference_image_paths=["/refs/hero1.png", "/refs/hero2.png"],
            sd_lora_name="hero_v3",
            ip_adapter_image_path="/refs/face.png",
            character_embedding_hash="sha256:abc",
        )
        data = char.to_dict()
        self.assertEqual(
            data["reference_image_paths"], ["/refs/hero1.png", "/refs/hero2.png"]
        )
        self.assertEqual(data["sd_lora_name"], "hero_v3")
        self.assertEqual(data["ip_adapter_image_path"], "/refs/face.png")
        self.assertEqual(data["character_embedding_hash"], "sha256:abc")

    def test_character_round_trips_through_dict(self) -> None:
        original = Character(
            character_id="c1",
            name="Hero",
            reference_image_paths=["/refs/a.png"],
            sd_lora_name="hero_v3",
            ip_adapter_image_path="/refs/face.png",
            character_embedding_hash="sha256:abc",
        )
        restored = Character.from_dict(original.to_dict())
        self.assertEqual(restored, original)

    def test_character_from_dict_tolerates_missing_reference_fields(self) -> None:
        legacy = {"character_id": "c1", "name": "Hero"}
        char = Character.from_dict(legacy)
        self.assertEqual(char.reference_image_paths, [])
        self.assertEqual(char.sd_lora_name, "")
        self.assertEqual(char.ip_adapter_image_path, "")
        self.assertEqual(char.character_embedding_hash, "")

    def test_project_save_load_preserves_character_reference_fields(self) -> None:
        ps = ProjectService()
        project = ps.create_project("Ref Test")
        project.characters.append(
            Character(
                character_id="c1",
                name="Hero",
                reference_image_paths=["/refs/h.png"],
                sd_lora_name="hero_v3",
                ip_adapter_image_path="/refs/face.png",
                character_embedding_hash="sha256:abc",
            )
        )

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "project.json"
            ps.save_project(project, str(path))
            loaded = ps.load_project(str(path))

        char = loaded.characters[0]
        self.assertEqual(char.reference_image_paths, ["/refs/h.png"])
        self.assertEqual(char.sd_lora_name, "hero_v3")
        self.assertEqual(char.ip_adapter_image_path, "/refs/face.png")
        self.assertEqual(char.character_embedding_hash, "sha256:abc")


if __name__ == "__main__":
    unittest.main()
