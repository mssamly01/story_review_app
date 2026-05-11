import unittest

from app.services.beat_generator_service import BeatGeneratorService
from app.services.project_service import ProjectService


def build_scene_project(*, importance: str = "high", target_beats: int = 6):
    project_service = ProjectService()
    project = project_service.create_project("Căn nhà cũ")
    chapter = project_service.add_source_chapter(
        project,
        title="Chương 1",
        chapter_number=1,
        raw_text="Lâm Vũ trở về căn nhà cũ. Cánh cửa cuối hành lang bị khóa.",
    )
    episode = project_service.add_review_episode(
        project,
        title="Cánh cửa cuối hành lang",
        source_chapter_ids=[chapter.chapter_id],
        tone="mysterious",
        density="balanced",
    )
    scene = project_service.add_scene(
        project,
        episode_id=episode.episode_id,
        title="Trở về nhà cũ",
        summary=("Lâm Vũ quay lại căn nhà cũ. " "Anh nhận ra cánh cửa cuối hành lang vẫn bị khóa."),
        characters=["lam_vu"],
        location="old_house_hallway",
        mood="mysterious",
        importance=importance,
        target_beats=target_beats,
    )
    return project_service, project, episode, scene


class BeatGeneratorServiceTests(unittest.TestCase):
    def test_generate_beats_for_scene(self) -> None:
        project_service, project, episode, scene = build_scene_project()
        service = BeatGeneratorService(project_service)

        beats = service.generate_beats_for_scene(
            project,
            episode.episode_id,
            scene.scene_id,
            retelling_density="full",
        )

        self.assertGreater(len(beats), 1)
        self.assertEqual(scene.beat_ids, [beat.beat_id for beat in beats])
        for index, beat in enumerate(beats, start=1):
            self.assertEqual(beat.scene_id, scene.scene_id)
            self.assertEqual(beat.order_index, index)
            self.assertNotEqual(beat.story_function, "")
            self.assertNotEqual(beat.action, "")
            self.assertNotIn("many things happen", beat.action.lower())
            self.assertNotEqual(beat.emotion, "")
            self.assertNotEqual(beat.shot_type, "")
            self.assertNotEqual(beat.visual_description, "")
            self.assertNotEqual(beat.continuity_tags, [])

    def test_generate_beats_for_episode(self) -> None:
        project_service, project, episode, first_scene = build_scene_project()
        second_scene = project_service.add_scene(
            project,
            episode_id=episode.episode_id,
            title="Căn phòng bị khóa",
            summary="Lâm Vũ nghe thấy tiếng động sau căn phòng bị khóa.",
            characters=["lam_vu"],
            location="old_house_hallway",
            mood="tense",
            importance="medium",
            target_beats=4,
        )
        service = BeatGeneratorService(project_service)

        beats = service.generate_beats_for_episode(
            project,
            episode.episode_id,
            retelling_density="balanced",
        )

        self.assertGreater(len(beats), 0)
        self.assertNotEqual(first_scene.beats, [])
        self.assertNotEqual(second_scene.beats, [])
        self.assertEqual(
            [beat.order_index for beat in first_scene.ordered_beats()],
            list(range(1, len(first_scene.beats) + 1)),
        )
        self.assertEqual(
            [beat.order_index for beat in second_scene.ordered_beats()],
            list(range(1, len(second_scene.beats) + 1)),
        )
        self.assertTrue(all(beat.beat_id.startswith("beat_sc_001_") for beat in first_scene.beats))
        self.assertTrue(all(beat.beat_id.startswith("beat_sc_002_") for beat in second_scene.beats))

    def test_retelling_density_affects_beat_count(self) -> None:
        project_service, project, episode, scene = build_scene_project(
            importance="high",
            target_beats=6,
        )
        service = BeatGeneratorService(project_service)

        full_count = len(
            service.generate_beats_for_scene(
                project,
                episode.episode_id,
                scene.scene_id,
                retelling_density="full",
            )
        )
        balanced_count = len(
            service.generate_beats_for_scene(
                project,
                episode.episode_id,
                scene.scene_id,
                retelling_density="balanced",
            )
        )
        condensed_count = len(
            service.generate_beats_for_scene(
                project,
                episode.episode_id,
                scene.scene_id,
                retelling_density="condensed",
            )
        )

        self.assertGreaterEqual(full_count, balanced_count)
        self.assertGreaterEqual(balanced_count, condensed_count)
        self.assertGreater(condensed_count, 1)

    def test_generated_beats_preserve_scene_context(self) -> None:
        project_service, project, episode, scene = build_scene_project()
        service = BeatGeneratorService(project_service)

        beats = service.generate_beats_for_scene(
            project,
            episode.episode_id,
            scene.scene_id,
            retelling_density="full",
        )

        for beat in beats:
            self.assertEqual(beat.characters, ["lam_vu"])
            self.assertEqual(beat.location, "old_house_hallway")
            self.assertIn(scene.scene_id, beat.continuity_tags)
            self.assertIn(episode.episode_id, beat.continuity_tags)
            self.assertIn("lam_vu", beat.continuity_tags)
            self.assertIn("old_house_hallway", beat.continuity_tags)
            self.assertIn("mysterious", beat.continuity_tags)

    def test_beat_generation_is_idempotent(self) -> None:
        project_service, project, episode, scene = build_scene_project()
        service = BeatGeneratorService(project_service)

        first_beats = service.generate_beats_for_scene(
            project,
            episode.episode_id,
            scene.scene_id,
            retelling_density="balanced",
        )
        first_payload = [beat.to_dict() for beat in first_beats]
        second_beats = service.generate_beats_for_scene(
            project,
            episode.episode_id,
            scene.scene_id,
            retelling_density="balanced",
        )
        second_payload = [beat.to_dict() for beat in second_beats]

        self.assertEqual(first_payload, second_payload)
        self.assertEqual(scene.beat_ids, [beat.beat_id for beat in second_beats])
        self.assertEqual(len(scene.beat_ids), len(set(scene.beat_ids)))

    def test_no_review_or_prompt_generation_yet(self) -> None:
        project_service, project, episode, scene = build_scene_project()
        service = BeatGeneratorService(project_service)

        beats = service.generate_beats_for_scene(
            project,
            episode.episode_id,
            scene.scene_id,
            retelling_density="full",
        )

        for beat in beats:
            self.assertEqual(beat.review_text, "")
            self.assertEqual(beat.image_prompt, "")
            self.assertEqual(beat.negative_prompt, "")

    def test_generate_beats_rejects_unknown_density(self) -> None:
        project_service, project, episode, scene = build_scene_project()
        service = BeatGeneratorService(project_service)

        with self.assertRaises(ValueError):
            service.generate_beats_for_scene(
                project,
                episode.episode_id,
                scene.scene_id,
                retelling_density="summary",
            )


if __name__ == "__main__":
    unittest.main()
