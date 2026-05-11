"""Tests for the ``Dialogue`` dataclass introduced in schema v3."""

from __future__ import annotations

import unittest

from app.domain.dialogue import DEFAULT_DIALOGUE_STYLE, DIALOGUE_STYLES, Dialogue


class DialogueConstructionTests(unittest.TestCase):
    def test_defaults_style_to_speech(self) -> None:
        dialogue = Dialogue(speaker_id="char_hero", line="Xin chào")
        self.assertEqual(dialogue.style, "speech")
        self.assertEqual(dialogue.style, DEFAULT_DIALOGUE_STYLE)

    def test_accepts_all_recognized_styles(self) -> None:
        for style in DIALOGUE_STYLES:
            with self.subTest(style=style):
                dialogue = Dialogue(speaker_id="char_hero", line="x", style=style)
                self.assertEqual(dialogue.style, style)


class DialogueRoundtripTests(unittest.TestCase):
    def test_to_dict_contains_three_fields(self) -> None:
        dialogue = Dialogue(speaker_id="char_villain", line="Đừng đến gần!", style="shout")
        self.assertEqual(
            dialogue.to_dict(),
            {"speaker_id": "char_villain", "line": "Đừng đến gần!", "style": "shout"},
        )

    def test_from_dict_round_trip(self) -> None:
        payload = {"speaker_id": "char_narrator", "line": "Đêm đó", "style": "narration"}
        rebuilt = Dialogue.from_dict(payload)
        self.assertEqual(rebuilt.speaker_id, "char_narrator")
        self.assertEqual(rebuilt.line, "Đêm đó")
        self.assertEqual(rebuilt.style, "narration")
        self.assertEqual(rebuilt.to_dict(), payload)

    def test_from_dict_missing_style_uses_default(self) -> None:
        rebuilt = Dialogue.from_dict({"speaker_id": "x", "line": "y"})
        self.assertEqual(rebuilt.style, DEFAULT_DIALOGUE_STYLE)

    def test_from_dict_empty_style_string_uses_default(self) -> None:
        rebuilt = Dialogue.from_dict({"speaker_id": "x", "line": "y", "style": ""})
        self.assertEqual(rebuilt.style, DEFAULT_DIALOGUE_STYLE)

    def test_from_dict_missing_fields_default_to_empty_strings(self) -> None:
        rebuilt = Dialogue.from_dict({})
        self.assertEqual(rebuilt.speaker_id, "")
        self.assertEqual(rebuilt.line, "")
        self.assertEqual(rebuilt.style, DEFAULT_DIALOGUE_STYLE)

    def test_from_dict_coerces_non_string_inputs(self) -> None:
        # Tolerate non-string speaker_id/line from older / hand-edited JSON.
        rebuilt = Dialogue.from_dict({"speaker_id": 42, "line": 7})
        self.assertEqual(rebuilt.speaker_id, "42")
        self.assertEqual(rebuilt.line, "7")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
