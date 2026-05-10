import json
import unittest

from app.infrastructure.ai_gateway import AIGateway
from app.infrastructure.mock_ai_gateway import MockAIGateway


class MockAIGatewayTests(unittest.TestCase):
    def test_mock_ai_gateway_generate_json_known_prompts(self) -> None:
        gateway = MockAIGateway()
        expected_top_level_keys = {
            "story_parser": {
                "detected_characters",
                "detected_locations",
                "scene_candidates",
                "important_events",
            },
            "episode_planner": {"episode", "scenes", "cliffhanger"},
            "beat_generator": {"beats"},
            "review_rewriter": {"rewritten_beats"},
            "image_prompt_builder": {"prompts"},
            "continuity_checker": {"issues"},
        }

        for prompt_name, keys in expected_top_level_keys.items():
            with self.subTest(prompt_name=prompt_name):
                result = gateway.generate_json(
                    prompt_name,
                    {
                        "chapter_id": "ch_001",
                        "source_chapter_ids": ["ch_001"],
                        "scene_id": "sc_001",
                        "beat_id": "b_001",
                    },
                )

                self.assertIsInstance(result, dict)
                self.assertTrue(keys.issubset(result.keys()))

    def test_mock_ai_gateway_rejects_unknown_prompt(self) -> None:
        gateway = MockAIGateway()

        with self.assertRaisesRegex(ValueError, "Unsupported prompt_name"):
            gateway.generate_json("unknown_prompt", {})

    def test_mock_ai_gateway_is_deterministic(self) -> None:
        gateway = MockAIGateway()
        input_data = {"chapter_id": "ch_001", "scene_id": "sc_001"}

        first = gateway.generate_json("beat_generator", input_data)
        second = gateway.generate_json("beat_generator", input_data)

        self.assertEqual(first, second)

    def test_mock_gateway_needs_no_network_or_credentials(self) -> None:
        gateway = MockAIGateway()

        result = gateway.generate_json("story_parser", {"chapter_id": "ch_001"})

        self.assertEqual(result["chapter_id"], "ch_001")
        self.assertIn("detected_characters", result)

    def test_generate_text_returns_serialized_json(self) -> None:
        gateway = MockAIGateway()

        text = gateway.generate_text("continuity_checker", {})

        self.assertEqual(json.loads(text), gateway.generate_json("continuity_checker", {}))

    def test_mock_gateway_satisfies_ai_gateway_protocol(self) -> None:
        gateway = MockAIGateway()

        self.assertIsInstance(gateway, AIGateway)


if __name__ == "__main__":
    unittest.main()

