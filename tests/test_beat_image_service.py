"""Tests for BeatImageService and BeatImageVariant domain extension.

Covers:
- BeatImageVariant round-trips through to_dict/from_dict
- attach_image stores variant + marks selected by default
- attach_image with select=False does NOT change current selection
- select_image moves selection between variants
- remove_image deletes only the named variant
- list_images returns all attached variants
- Project JSON round-trips beats with attached images (Rule 5 — human readable)
- Beat.image_path / Beat.selected_image properties reflect current state
- AGENTS.md Rule 6: source raw_text untouched after image attach
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.domain.beat import Beat, BeatImageVariant
from app.domain.character import Character
from app.domain.episode import ReviewEpisode
from app.domain.location import Location
from app.domain.scene import Scene
from app.domain.source_chapter import SourceChapter
from app.services.beat_image_service import BeatImageService
from app.services.project_service import ProjectService


class _Fixture:
    @staticmethod
    def project_with_one_beat() -> tuple[ProjectService, "Project"]:
        from app.domain.project import Project  # local import to avoid circular

        ps = ProjectService()
        project = ps.create_project("Image Loop Test")
        project.source_chapters.append(
            SourceChapter(
                chapter_id="ch1",
                title="C1",
                chapter_number=1,
                raw_text="A character walks into a castle.",
            )
        )
        project.characters.append(
            Character(character_id="char_hero", name="Hero")
        )
        project.locations.append(
            Location(location_id="loc_castle", name="Castle")
        )
        episode = ReviewEpisode(
            episode_id="ep1",
            title="Ep1",
            summary="",
            source_chapter_ids=["ch1"],
        )
        scene = Scene(
            scene_id="sc1",
            episode_id="ep1",
            title="Walk in",
            summary="",
            location="loc_castle",
            characters=["char_hero"],
        )
        scene.beats.append(
            Beat(
                beat_id="beat_001",
                scene_id="sc1",
                order_index=1,
                image_prompt="hero walking into castle, cinematic",
                negative_prompt="low quality, blurry",
            )
        )
        episode.scenes.append(scene)
        project.review_episodes.append(episode)
        return ps, project


class BeatImageVariantTests(unittest.TestCase):
    def test_variant_round_trips_through_to_dict_and_from_dict(self) -> None:
        variant = BeatImageVariant(
            image_id="img_abc",
            image_path="/tmp/x.png",
            model="sdxl",
            seed="42",
            generated_at="2025-11-01T00:00:00Z",
            selected=True,
            notes="hero shot, take 3",
        )
        data = variant.to_dict()
        restored = BeatImageVariant.from_dict(data)
        self.assertEqual(restored, variant)

    def test_variant_defaults_to_unselected(self) -> None:
        variant = BeatImageVariant(image_id="img_1", image_path="/tmp/y.png")
        self.assertFalse(variant.selected)


class BeatImageServiceTests(unittest.TestCase):
    def test_attach_image_adds_variant_and_marks_selected_by_default(self) -> None:
        ps, project = _Fixture.project_with_one_beat()
        service = BeatImageService(ps)

        variant = service.attach_image(
            project,
            "beat_001",
            "/tmp/hero_v1.png",
            model="sdxl",
            seed="42",
        )

        beat = project.review_episodes[0].scenes[0].beats[0]
        self.assertEqual(len(beat.images), 1)
        self.assertTrue(variant.selected)
        self.assertEqual(beat.selected_image, variant)
        self.assertEqual(beat.image_path, "/tmp/hero_v1.png")
        self.assertEqual(variant.model, "sdxl")
        self.assertEqual(variant.seed, "42")
        self.assertTrue(variant.generated_at, "should record generation timestamp")

    def test_attach_image_with_no_select_preserves_current_selection(self) -> None:
        ps, project = _Fixture.project_with_one_beat()
        service = BeatImageService(ps)
        first = service.attach_image(project, "beat_001", "/tmp/a.png")

        second = service.attach_image(
            project, "beat_001", "/tmp/b.png", select=False
        )

        beat = project.review_episodes[0].scenes[0].beats[0]
        self.assertEqual(len(beat.images), 2)
        self.assertTrue(first.selected)
        self.assertFalse(second.selected)
        self.assertEqual(beat.selected_image, first)

    def test_select_image_moves_selection_between_variants(self) -> None:
        ps, project = _Fixture.project_with_one_beat()
        service = BeatImageService(ps)
        first = service.attach_image(project, "beat_001", "/tmp/a.png")
        second = service.attach_image(
            project, "beat_001", "/tmp/b.png", select=False
        )

        service.select_image(project, "beat_001", second.image_id)

        beat = project.review_episodes[0].scenes[0].beats[0]
        self.assertFalse(first.selected)
        self.assertTrue(second.selected)
        self.assertEqual(beat.image_path, "/tmp/b.png")

    def test_remove_image_deletes_only_named_variant(self) -> None:
        ps, project = _Fixture.project_with_one_beat()
        service = BeatImageService(ps)
        first = service.attach_image(project, "beat_001", "/tmp/a.png")
        second = service.attach_image(
            project, "beat_001", "/tmp/b.png", select=False
        )

        service.remove_image(project, "beat_001", first.image_id)

        beat = project.review_episodes[0].scenes[0].beats[0]
        self.assertEqual(len(beat.images), 1)
        self.assertEqual(beat.images[0].image_id, second.image_id)

    def test_attach_image_raises_for_unknown_beat(self) -> None:
        ps, project = _Fixture.project_with_one_beat()
        with self.assertRaises(LookupError):
            BeatImageService(ps).attach_image(
                project, "beat_does_not_exist", "/tmp/x.png"
            )

    def test_select_image_raises_for_unknown_image_id(self) -> None:
        ps, project = _Fixture.project_with_one_beat()
        with self.assertRaises(LookupError):
            BeatImageService(ps).select_image(
                project, "beat_001", "img_does_not_exist"
            )

    def test_list_images_returns_all_attached_variants(self) -> None:
        ps, project = _Fixture.project_with_one_beat()
        service = BeatImageService(ps)
        service.attach_image(project, "beat_001", "/tmp/a.png")
        service.attach_image(project, "beat_001", "/tmp/b.png", select=False)

        variants = service.list_images(project, "beat_001")
        self.assertEqual(len(variants), 2)


class BeatImagePersistenceTests(unittest.TestCase):
    def test_project_json_round_trips_beats_with_images(self) -> None:
        ps, project = _Fixture.project_with_one_beat()
        BeatImageService(ps).attach_image(
            project,
            "beat_001",
            "/tmp/hero_v1.png",
            model="sdxl",
            seed="42",
            notes="take 1",
        )

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "project.json"
            ps.save_project(project, str(path))
            loaded = ps.load_project(str(path))

        beat = loaded.review_episodes[0].scenes[0].beats[0]
        self.assertEqual(len(beat.images), 1)
        variant = beat.images[0]
        self.assertEqual(variant.image_path, "/tmp/hero_v1.png")
        self.assertEqual(variant.model, "sdxl")
        self.assertEqual(variant.seed, "42")
        self.assertEqual(variant.notes, "take 1")
        self.assertTrue(variant.selected)
        self.assertEqual(beat.image_path, "/tmp/hero_v1.png")

    def test_image_attach_does_not_modify_source_raw_text(self) -> None:
        ps, project = _Fixture.project_with_one_beat()
        original_text = project.source_chapters[0].raw_text
        BeatImageService(ps).attach_image(project, "beat_001", "/tmp/x.png")
        self.assertEqual(project.source_chapters[0].raw_text, original_text)


if __name__ == "__main__":
    unittest.main()
