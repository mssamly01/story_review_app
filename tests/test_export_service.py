import unittest

from app.services.export_service import ExportService
from app.services.project_service import ProjectService


class ExportServiceTests(unittest.TestCase):
    def test_episode_markdown_contains_review_text_and_image_prompt(self) -> None:
        project_service = ProjectService()
        export_service = ExportService(project_service)
        project = project_service.create_project("Căn nhà cũ")
        chapter = project_service.add_source_chapter(
            project,
            title="Chương 1",
            chapter_number=1,
            raw_text="Lâm Vũ trở về căn nhà cũ.",
        )
        episode = project_service.add_review_episode(
            project,
            title="Cánh cửa cuối hành lang",
            source_chapter_ids=[chapter.chapter_id],
        )
        scene = project_service.add_scene(
            project,
            episode_id=episode.episode_id,
            title="Trở về",
            location="old_house",
            mood="lonely, mysterious",
        )
        project_service.add_beat(
            project,
            episode_id=episode.episode_id,
            scene_id=scene.scene_id,
            story_function="opening",
            characters=["lam_vu"],
            location="old_house",
            emotion="lonely",
            shot_type="wide shot",
            review_text="Lâm Vũ quay lại căn nhà mà ông nội để lại.",
            image_prompt=(
                "dark fantasy webtoon style, young man standing before an old house"
            ),
            negative_prompt="low quality, blurry, text",
        )

        markdown = export_service.export_episode_to_markdown(
            project, episode.episode_id
        )

        self.assertIn("# Cánh cửa cuối hành lang", markdown)
        self.assertIn("## Scene 1 - Trở về", markdown)
        self.assertIn("### Beat 1 - `b_001`", markdown)
        self.assertIn("Review text:", markdown)
        self.assertIn("Lâm Vũ quay lại căn nhà mà ông nội để lại.", markdown)
        self.assertIn("Image prompt:", markdown)
        self.assertIn(
            "dark fantasy webtoon style, young man standing before an old house",
            markdown,
        )


if __name__ == "__main__":
    unittest.main()
