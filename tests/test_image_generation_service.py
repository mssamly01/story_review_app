"""Tests for ImageGenerationService (P2.4).

These tests use a fake ``ImageGateway`` so no ComfyUI server is needed. They
focus on the orchestration behaviour:

* The service finds the right beat in the project tree.
* It refuses to render when ``Beat.image_prompt`` is empty.
* It chooses a seed (caller-provided or via ``seed_provider``) and records it
  on the resulting :class:`BeatImageVariant`.
* It writes the gateway's bytes to ``output_dir`` and attaches the file path
  back onto the beat via :class:`BeatImageService`, marking it selected by
  default but honouring ``select=False``.
* It does not mutate ``SourceChapter.raw_text`` (AGENTS.md Rule 6).
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.domain.beat import Beat
from app.domain.character import Character
from app.domain.episode import ReviewEpisode
from app.domain.location import Location
from app.domain.project import Project
from app.domain.scene import Scene
from app.domain.source_chapter import SourceChapter
from app.services.beat_image_service import BeatImageService
from app.services.image_generation_service import ImageGenerationService
from app.services.project_service import ProjectService


class _FakeImageGateway:
    """Records every call and returns deterministic bytes per seed."""

    def __init__(self, *, bytes_per_seed: dict[int, bytes] | None = None) -> None:
        self.calls: list[tuple[str, str, int | None]] = []
        self._bytes_per_seed = bytes_per_seed or {}

    def generate(
        self,
        prompt: str,
        negative_prompt: str,
        *,
        seed: int | None = None,
    ) -> bytes:
        self.calls.append((prompt, negative_prompt, seed))
        return self._bytes_per_seed.get(
            seed if seed is not None else -1,
            f"PNG:{prompt}|{negative_prompt}|{seed}".encode("utf-8"),
        )


class _Fixture:
    @staticmethod
    def project_with_one_prompted_beat() -> tuple[ProjectService, Project]:
        ps = ProjectService()
        project = ps.create_project("ImageGen P2.4")
        project.source_chapters.append(
            SourceChapter(
                chapter_id="ch1",
                title="C1",
                chapter_number=1,
                raw_text="Original source paragraph — must stay intact.",
            )
        )
        project.characters.append(Character(character_id="char_hero", name="Hero"))
        project.locations.append(Location(location_id="loc_castle", name="Castle"))
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
                image_prompt="hero walking into castle, cinematic webtoon style",
                negative_prompt="low quality, blurry",
            )
        )
        episode.scenes.append(scene)
        project.review_episodes.append(episode)
        return ps, project


class RenderBeatHappyPathTests(unittest.TestCase):
    def test_render_attaches_variant_with_seed_and_writes_file(self) -> None:
        ps, project = _Fixture.project_with_one_prompted_beat()
        gateway = _FakeImageGateway()

        with TemporaryDirectory() as tmp:
            service = ImageGenerationService(
                image_gateway=gateway,
                beat_image_service=BeatImageService(ps),
                output_dir=tmp,
                model_label="comfyui",
                seed_provider=lambda: 4242,
            )
            variant = service.render_beat(project, "beat_001")

            # Gateway was called with the beat's prompts and the seed.
            self.assertEqual(
                gateway.calls,
                [
                    (
                        "hero walking into castle, cinematic webtoon style",
                        "low quality, blurry",
                        4242,
                    )
                ],
            )

            beat = project.review_episodes[0].scenes[0].beats[0]
            self.assertEqual(len(beat.images), 1)
            self.assertIs(beat.images[0], variant)
            self.assertTrue(variant.selected)
            self.assertEqual(variant.model, "comfyui")
            self.assertEqual(variant.seed, "4242")
            self.assertTrue(variant.generated_at)

            file_path = Path(variant.image_path)
            self.assertTrue(file_path.exists())
            self.assertTrue(file_path.is_file())
            self.assertEqual(file_path.parent, Path(tmp))
            self.assertTrue(file_path.name.startswith("beat_001_"))
            self.assertTrue(file_path.name.endswith("_4242.png"))
            self.assertEqual(
                file_path.read_bytes(),
                b"PNG:hero walking into castle, cinematic webtoon style|"
                b"low quality, blurry|4242",
            )

    def test_explicit_seed_overrides_seed_provider(self) -> None:
        ps, project = _Fixture.project_with_one_prompted_beat()
        gateway = _FakeImageGateway()
        with TemporaryDirectory() as tmp:
            service = ImageGenerationService(
                image_gateway=gateway,
                beat_image_service=BeatImageService(ps),
                output_dir=tmp,
                seed_provider=lambda: 999,
            )
            variant = service.render_beat(project, "beat_001", seed=7)

            self.assertEqual(gateway.calls[0][2], 7)
            self.assertEqual(variant.seed, "7")

    def test_select_false_does_not_change_existing_selection(self) -> None:
        ps, project = _Fixture.project_with_one_prompted_beat()
        # Pre-attach a "manual import" variant that is currently selected.
        beat_image_service = BeatImageService(ps)
        beat_image_service.attach_image(
            project, "beat_001", "/tmp/manual.png", model="midjourney", seed="111"
        )

        gateway = _FakeImageGateway()
        with TemporaryDirectory() as tmp:
            service = ImageGenerationService(
                image_gateway=gateway,
                beat_image_service=beat_image_service,
                output_dir=tmp,
                seed_provider=lambda: 5555,
            )
            second = service.render_beat(project, "beat_001", select=False)

        beat = project.review_episodes[0].scenes[0].beats[0]
        self.assertEqual(len(beat.images), 2)
        self.assertFalse(second.selected)
        # Original manual variant is still the selected one.
        self.assertEqual(beat.selected_image.model, "midjourney")

    def test_render_uses_default_model_label_when_not_set(self) -> None:
        ps, project = _Fixture.project_with_one_prompted_beat()
        with TemporaryDirectory() as tmp:
            service = ImageGenerationService(
                image_gateway=_FakeImageGateway(),
                beat_image_service=BeatImageService(ps),
                output_dir=tmp,
                seed_provider=lambda: 1,
            )
            variant = service.render_beat(project, "beat_001")
        self.assertEqual(variant.model, ImageGenerationService.DEFAULT_MODEL_LABEL)

    def test_render_creates_output_dir_if_missing(self) -> None:
        ps, project = _Fixture.project_with_one_prompted_beat()
        with TemporaryDirectory() as tmp:
            nested = Path(tmp) / "out" / "nested"
            service = ImageGenerationService(
                image_gateway=_FakeImageGateway(),
                beat_image_service=BeatImageService(ps),
                output_dir=nested,
                seed_provider=lambda: 1,
            )
            variant = service.render_beat(project, "beat_001")
            self.assertTrue(nested.exists())
            self.assertTrue(Path(variant.image_path).exists())


class RenderBeatErrorTests(unittest.TestCase):
    def test_unknown_beat_raises_lookup_error(self) -> None:
        ps, project = _Fixture.project_with_one_prompted_beat()
        service = ImageGenerationService(
            image_gateway=_FakeImageGateway(),
            beat_image_service=BeatImageService(ps),
            output_dir="ignored",
            seed_provider=lambda: 1,
        )
        with self.assertRaises(LookupError):
            service.render_beat(project, "beat_does_not_exist")

    def test_empty_image_prompt_raises_value_error(self) -> None:
        ps, project = _Fixture.project_with_one_prompted_beat()
        project.review_episodes[0].scenes[0].beats[0].image_prompt = "   "

        service = ImageGenerationService(
            image_gateway=_FakeImageGateway(),
            beat_image_service=BeatImageService(ps),
            output_dir="ignored",
            seed_provider=lambda: 1,
        )
        with self.assertRaises(ValueError):
            service.render_beat(project, "beat_001")

    def test_empty_bytes_from_gateway_raises_value_error(self) -> None:
        ps, project = _Fixture.project_with_one_prompted_beat()
        gateway = _FakeImageGateway(bytes_per_seed={42: b""})
        with TemporaryDirectory() as tmp:
            service = ImageGenerationService(
                image_gateway=gateway,
                beat_image_service=BeatImageService(ps),
                output_dir=tmp,
                seed_provider=lambda: 42,
            )
            with self.assertRaises(ValueError):
                service.render_beat(project, "beat_001")
            # Nothing was attached because gateway returned empty.
            beat = project.review_episodes[0].scenes[0].beats[0]
            self.assertEqual(beat.images, [])


class RenderBeatGuardRailTests(unittest.TestCase):
    """AGENTS.md guard rails the service must respect."""

    def test_render_does_not_mutate_source_chapter_raw_text(self) -> None:
        # Rule 6: source text bất khả xâm phạm.
        ps, project = _Fixture.project_with_one_prompted_beat()
        original_raw = project.source_chapters[0].raw_text
        with TemporaryDirectory() as tmp:
            service = ImageGenerationService(
                image_gateway=_FakeImageGateway(),
                beat_image_service=BeatImageService(ps),
                output_dir=tmp,
                seed_provider=lambda: 1,
            )
            service.render_beat(project, "beat_001")
        self.assertEqual(project.source_chapters[0].raw_text, original_raw)

    def test_render_does_not_overwrite_existing_image_prompt(self) -> None:
        # Rule 3: prompts come from PromptBuilderService; the render service
        # must consume them, not rewrite them.
        ps, project = _Fixture.project_with_one_prompted_beat()
        beat = project.review_episodes[0].scenes[0].beats[0]
        original_prompt = beat.image_prompt
        original_negative = beat.negative_prompt
        with TemporaryDirectory() as tmp:
            service = ImageGenerationService(
                image_gateway=_FakeImageGateway(),
                beat_image_service=BeatImageService(ps),
                output_dir=tmp,
                seed_provider=lambda: 1,
            )
            service.render_beat(project, "beat_001")
        self.assertEqual(beat.image_prompt, original_prompt)
        self.assertEqual(beat.negative_prompt, original_negative)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
