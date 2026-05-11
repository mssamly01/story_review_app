import os
import unittest
from unittest.mock import patch

from app.infrastructure.ai_gateway_factory import create_ai_gateway
from app.infrastructure.anthropic_ai_gateway import AnthropicAIGateway
from app.infrastructure.gemini_ai_gateway import GeminiAIGateway
from app.infrastructure.mock_ai_gateway import MockAIGateway
from app.infrastructure.ollama_ai_gateway import OllamaAIGateway
from app.infrastructure.openai_ai_gateway import (
    AIConfigurationError,
    OpenAIAIGateway,
)


class AIGatewayFactoryTests(unittest.TestCase):
    def test_ai_gateway_factory_returns_none_when_use_ai_false(self) -> None:
        self.assertIsNone(create_ai_gateway(False))

    def test_ai_gateway_factory_returns_mock_gateway(self) -> None:
        gateway = create_ai_gateway(True, mock_ai=True)

        self.assertIsInstance(gateway, MockAIGateway)

    def test_ai_gateway_factory_rejects_mock_and_real_together(self) -> None:
        with self.assertRaisesRegex(ValueError, "either --mock-ai or --real-ai"):
            create_ai_gateway(True, mock_ai=True, real_ai=True)

    def test_ai_gateway_factory_rejects_ambiguous_ai_mode(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires either"):
            create_ai_gateway(True)

    def test_ai_gateway_factory_returns_real_gateway_when_configured(self) -> None:
        env_name = "OPENAI_" + "API_KEY"
        with patch.dict(os.environ, {env_name: "test-secret"}, clear=True):
            gateway = create_ai_gateway(True, real_ai=True, model="test-model")

        self.assertIsInstance(gateway, OpenAIAIGateway)
        self.assertEqual(gateway.model, "test-model")

    def test_ai_gateway_factory_real_mode_requires_configuration(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(AIConfigurationError):
                create_ai_gateway(True, real_ai=True)


_ANTHROPIC_ENV = "ANTHROPIC_" + "API_KEY"
_GEMINI_ENV = "GEMINI_" + "API_KEY"


class AIGatewayProviderRoutingTests(unittest.TestCase):
    """Provider routing for ``--real-ai --provider {anthropic,gemini,ollama}``."""

    def test_provider_anthropic_returns_anthropic_gateway(self) -> None:
        with patch.dict(os.environ, {_ANTHROPIC_ENV: "k"}, clear=True):
            gateway = create_ai_gateway(True, real_ai=True, provider="anthropic")
        self.assertIsInstance(gateway, AnthropicAIGateway)

    def test_provider_gemini_returns_gemini_gateway(self) -> None:
        with patch.dict(os.environ, {_GEMINI_ENV: "k"}, clear=True):
            gateway = create_ai_gateway(True, real_ai=True, provider="gemini")
        self.assertIsInstance(gateway, GeminiAIGateway)

    def test_provider_ollama_returns_ollama_gateway(self) -> None:
        # Ollama needs no credentials, so an empty env is fine.
        with patch.dict(os.environ, {}, clear=True):
            gateway = create_ai_gateway(True, real_ai=True, provider="ollama")
        self.assertIsInstance(gateway, OllamaAIGateway)

    def test_provider_argument_is_case_insensitive(self) -> None:
        with patch.dict(os.environ, {_ANTHROPIC_ENV: "k"}, clear=True):
            gateway = create_ai_gateway(True, real_ai=True, provider="Anthropic")
        self.assertIsInstance(gateway, AnthropicAIGateway)

    def test_provider_env_var_used_when_no_explicit_provider(self) -> None:
        with patch.dict(
            os.environ,
            {"AI_PROVIDER": "anthropic", _ANTHROPIC_ENV: "k"},
            clear=True,
        ):
            gateway = create_ai_gateway(True, real_ai=True)
        self.assertIsInstance(gateway, AnthropicAIGateway)

    def test_unknown_provider_raises_value_error(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "Unsupported AI provider"):
                create_ai_gateway(True, real_ai=True, provider="dall-e")

    def test_explicit_provider_overrides_env(self) -> None:
        # AI_PROVIDER points one way; explicit kwarg wins.
        env = {
            "AI_PROVIDER": "anthropic",
            _GEMINI_ENV: "k",
        }
        with patch.dict(os.environ, env, clear=True):
            gateway = create_ai_gateway(True, real_ai=True, provider="gemini")
        self.assertIsInstance(gateway, GeminiAIGateway)


if __name__ == "__main__":
    unittest.main()
