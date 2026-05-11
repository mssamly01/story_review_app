import os
from unittest.mock import patch
import unittest

from app.infrastructure.openai_ai_gateway import (
    AIConfigurationError,
    AIResponseParseError,
    OpenAIAIGateway,
)


class RecordingPromptLoader:
    def __init__(self) -> None:
        self.loaded_names: list[str] = []

    def load(self, prompt_name: str) -> str:
        self.loaded_names.append(prompt_name)
        return f"Template marker for {prompt_name}"


class RecordingProviderGateway(OpenAIAIGateway):
    def __init__(self, response_text: str, prompt_loader: RecordingPromptLoader):
        self.response_text = response_text
        self.calls: list[dict[str, str | None]] = []
        super().__init__("test-secret", "test-model", prompt_loader)

    def _call_model(self, prompt: str, system_message: str | None) -> str:
        self.calls.append(
            {
                "prompt": prompt,
                "system_message": system_message,
            }
        )
        return self.response_text


class OpenAIGatewayContractTests(unittest.TestCase):
    def test_openai_gateway_requires_configuration(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(AIConfigurationError, "Real AI mode requires"):
                OpenAIAIGateway()

    def test_openai_gateway_generate_json_parses_mocked_response(self) -> None:
        loader = RecordingPromptLoader()
        gateway = RecordingProviderGateway('{"ok": true}', loader)

        result = gateway.generate_json("story_parser", {"chapter_id": "ch_001"})

        self.assertEqual(result, {"ok": True})
        self.assertEqual(loader.loaded_names, ["story_parser"])

    def test_openai_gateway_generate_json_invalid_response_has_clear_error(
        self,
    ) -> None:
        loader = RecordingPromptLoader()
        gateway = RecordingProviderGateway("not valid json", loader)

        with self.assertRaisesRegex(AIResponseParseError, "not valid JSON"):
            gateway.generate_json("story_parser", {"chapter_id": "ch_001"})

    def test_openai_gateway_loads_prompt_template(self) -> None:
        loader = RecordingPromptLoader()
        gateway = RecordingProviderGateway('{"ok": true}', loader)

        gateway.generate_json(
            "review_rewriter",
            {"beat_id": "b_001"},
            system_message="System message",
        )

        self.assertEqual(loader.loaded_names, ["review_rewriter"])
        self.assertTrue(gateway.calls)
        self.assertIn("Template marker for review_rewriter", gateway.calls[0]["prompt"])
        self.assertIn('"beat_id": "b_001"', gateway.calls[0]["prompt"])
        self.assertEqual(gateway.calls[0]["system_message"], "System message")


if __name__ == "__main__":
    unittest.main()

