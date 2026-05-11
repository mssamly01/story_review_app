import unittest

from app.domain.source_chapter import SourceChapter
from app.services.story_parser_service import (
    ParsedChapterResult,
    StoryParserService,
)


class StoryParserServiceTests(unittest.TestCase):
    def test_parse_returns_future_ai_compatible_schema(self) -> None:
        chapter = SourceChapter(
            chapter_id="ch_001",
            title="Chương 1",
            chapter_number=1,
            raw_text=(
                "Lâm Vũ trở về căn nhà cũ sau nhiều năm xa cách. "
                "Anh nghe thấy một tiếng động kỳ lạ ở hành lang cuối.\n\n"
                "Lâm Vũ phát hiện căn phòng bị khóa. "
                "Ông Nội xuất hiện sau lưng anh."
            ),
        )
        service = StoryParserService()

        result = service.parse(chapter)

        self.assertIsInstance(result, ParsedChapterResult)
        self.assertEqual(result.chapter_id, "ch_001")
        self.assertEqual(
            [character.name for character in result.detected_characters],
            ["Lâm Vũ", "Ông Nội"],
        )
        self.assertEqual(
            [location.name for location in result.detected_locations],
            ["căn nhà cũ", "hành lang cuối", "căn phòng bị khóa"],
        )
        self.assertEqual(len(result.important_events), 4)
        self.assertEqual(len(result.scene_candidates), 2)

        data = result.to_dict()
        self.assertEqual(
            set(data.keys()),
            {
                "chapter_id",
                "detected_characters",
                "detected_locations",
                "scene_candidates",
                "important_events",
            },
        )
        self.assertEqual(
            set(data["detected_characters"][0].keys()),
            {"name", "role", "evidence", "confidence"},
        )
        self.assertEqual(
            set(data["detected_locations"][0].keys()),
            {"name", "mood", "evidence", "confidence"},
        )
        self.assertEqual(
            set(data["scene_candidates"][0].keys()),
            {
                "scene_id",
                "title",
                "summary",
                "mood",
                "characters",
                "location",
                "important_events",
                "importance",
            },
        )
        self.assertEqual(
            set(data["important_events"][0].keys()),
            {
                "event_id",
                "summary",
                "characters",
                "location",
                "evidence",
                "importance",
            },
        )

    def test_parse_is_deterministic_and_does_not_modify_source(self) -> None:
        raw_text = "Lâm Vũ bước vào căn nhà cũ. Anh nhận ra nơi này rất lạ."
        chapter = SourceChapter(
            chapter_id="ch_002",
            title="Chương 2",
            chapter_number=2,
            raw_text=raw_text,
        )
        service = StoryParserService()

        first_result = service.parse(chapter)
        second_result = service.parse(chapter)

        self.assertEqual(first_result.to_dict(), second_result.to_dict())
        self.assertEqual(chapter.raw_text, raw_text)
        self.assertEqual(chapter.parsed_scene_ids, [])

    def test_parse_empty_source_returns_empty_structures(self) -> None:
        chapter = SourceChapter(
            chapter_id="ch_empty",
            title="Chương trống",
            chapter_number=1,
            raw_text="   ",
        )
        service = StoryParserService()

        result = service.parse(chapter)

        self.assertEqual(result.chapter_id, "ch_empty")
        self.assertEqual(result.detected_characters, [])
        self.assertEqual(result.detected_locations, [])
        self.assertEqual(result.scene_candidates, [])
        self.assertEqual(result.important_events, [])


if __name__ == "__main__":
    unittest.main()
