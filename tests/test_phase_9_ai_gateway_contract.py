from pathlib import Path
import unittest

from app.infrastructure.mock_ai_gateway import MockAIGateway
from app.infrastructure.prompt_template_loader import PromptTemplateLoader


ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = ROOT / "app" / "prompts"


class PhaseNineAIGatewayContractTests(unittest.TestCase):
    def test_prompt_templates_follow_product_direction(self) -> None:
        forbidden_terms = [
            "video editor",
            "timeline",
            "audio track",
            "ffmpeg",
            "render video",
            "media clip",
        ]
        required_direction_terms = [
            "review narration",
            "beat",
            "scene",
            "image prompt",
        ]

        for path in sorted(PROMPTS_DIR.glob("*_prompt.md")):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8").lower()

                for forbidden_term in forbidden_terms:
                    self.assertNotIn(forbidden_term, text)
                self.assertTrue(
                    any(term in text for term in required_direction_terms),
                    f"{path.name} should mention the story review workflow.",
                )

    def test_phase_9_known_prompt_names_match_loader_and_gateway(self) -> None:
        loader_prompt_names = set(PromptTemplateLoader.PROMPT_FILES)
        gateway_prompt_names = set(MockAIGateway.SUPPORTED_PROMPTS)

        self.assertEqual(loader_prompt_names, gateway_prompt_names)

    def test_phase_9_generate_text_is_deterministic_for_contract_prompts(self) -> None:
        gateway = MockAIGateway()

        for prompt_name in sorted(MockAIGateway.SUPPORTED_PROMPTS):
            with self.subTest(prompt_name=prompt_name):
                input_data = {
                    "chapter_id": "ch_001",
                    "source_chapter_ids": ["ch_001"],
                    "scene_id": "sc_001",
                    "beat_id": "b_001",
                }

                first = gateway.generate_text(prompt_name, input_data)
                second = gateway.generate_text(prompt_name, input_data)

                self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
