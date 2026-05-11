import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.services.project_service import ProjectService
from app.services.source_import_service import SourceImportService


class SourceImportServiceTests(unittest.TestCase):
    def test_import_raw_text_adds_source_chapter_with_word_count(self) -> None:
        project_service = ProjectService()
        import_service = SourceImportService(project_service)
        project = project_service.create_project("Căn nhà cũ")
        raw_text = "Lâm Vũ trở về.\n\nCánh cửa cuối hành lang vẫn bị khóa."

        chapter = import_service.import_raw_text(
            project,
            title="Chương 1",
            chapter_number=1,
            raw_text=raw_text,
            notes="Imported from pasted manuscript.",
        )

        self.assertEqual(chapter.chapter_id, "ch_001")
        self.assertEqual(chapter.title, "Chương 1")
        self.assertEqual(chapter.chapter_number, 1)
        self.assertEqual(chapter.raw_text, raw_text)
        self.assertEqual(chapter.word_count, len(raw_text.split()))
        self.assertEqual(chapter.notes, "Imported from pasted manuscript.")
        self.assertEqual(project.source_chapters, [chapter])

    def test_import_raw_text_does_not_create_story_structure(self) -> None:
        project_service = ProjectService()
        import_service = SourceImportService(project_service)
        project = project_service.create_project("Căn nhà cũ")

        chapter = import_service.import_raw_text(
            project,
            title="Chương 1",
            chapter_number=1,
            raw_text="Lâm Vũ đứng trước căn nhà cũ.",
        )

        self.assertEqual(chapter.parsed_scene_ids, [])
        self.assertEqual(project.review_episodes, [])
        self.assertEqual(project.characters, [])
        self.assertEqual(project.locations, [])

    def test_imported_chapter_word_count_is_saved_to_json(self) -> None:
        project_service = ProjectService()
        import_service = SourceImportService(project_service)
        project = project_service.create_project("Căn nhà cũ")
        raw_text = "Một tiếng động vang lên sau cánh cửa."
        import_service.import_raw_text(
            project,
            title="Chương 2",
            chapter_number=2,
            raw_text=raw_text,
        )

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.json"
            project_service.save_project(project, path)
            data = json.loads(path.read_text(encoding="utf-8"))

        saved_chapter = data["source_chapters"][0]
        self.assertEqual(saved_chapter["title"], "Chương 2")
        self.assertEqual(saved_chapter["chapter_number"], 2)
        self.assertEqual(saved_chapter["raw_text"], raw_text)
        self.assertEqual(saved_chapter["word_count"], len(raw_text.split()))

    def test_import_raw_text_rejects_invalid_chapter_metadata(self) -> None:
        project_service = ProjectService()
        import_service = SourceImportService(project_service)
        project = project_service.create_project("Căn nhà cũ")

        with self.assertRaises(ValueError):
            import_service.import_raw_text(
                project,
                title="",
                chapter_number=1,
                raw_text="Text still belongs to source only.",
            )

        with self.assertRaises(ValueError):
            import_service.import_raw_text(
                project,
                title="Chương 0",
                chapter_number=0,
                raw_text="Text still belongs to source only.",
            )


if __name__ == "__main__":
    unittest.main()
