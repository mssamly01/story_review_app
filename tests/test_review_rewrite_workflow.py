import unittest

from app.services.beat_generator_service import BeatGeneratorService
from app.services.episode_planner_service import EpisodePlannerService
from app.services.project_service import ProjectService
from app.services.review_rewriter_service import ReviewRewriterService


class ReviewRewriteWorkflowTests(unittest.TestCase):
    def test_phase_6_rewrites_generated_beats_only_as_review_text(self) -> None:
        project_service = ProjectService()
        planner = EpisodePlannerService(project_service)
        beat_generator = BeatGeneratorService(project_service)
        rewriter = ReviewRewriterService()
        project = project_service.create_project("Căn nhà cũ")
        chapter = project_service.add_source_chapter(
            project,
            title="Chương 1",
            chapter_number=1,
            raw_text=(
                "Lâm Vũ trở về căn nhà cũ sau nhiều năm xa cách. "
                "Anh nghe thấy tiếng động lạ phía sau cánh cửa bị khóa."
            ),
        )
        raw_text = chapter.raw_text
        episode = planner.plan_episode(
            project,
            selected_source_chapter_ids=[chapter.chapter_id],
            narration_style="mysterious",
            retelling_density="full",
        )
        beats = beat_generator.generate_beats_for_episode(
            project,
            episode.episode_id,
            retelling_density="balanced",
        )

        rewritten_beats = rewriter.rewrite_episode(project, episode.episode_id)

        self.assertEqual(rewritten_beats, beats)
        self.assertTrue(all(beat.review_text for beat in rewritten_beats))
        self.assertTrue(all(beat.image_prompt == "" for beat in rewritten_beats))
        self.assertTrue(all(beat.negative_prompt == "" for beat in rewritten_beats))
        self.assertEqual(chapter.raw_text, raw_text)
        self.assertEqual(sum(len(scene.beats) for scene in episode.scenes), len(beats))


if __name__ == "__main__":
    unittest.main()
