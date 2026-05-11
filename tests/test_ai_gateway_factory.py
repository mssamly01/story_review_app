from unittest.mock import patch
import os
import unittest

from app.infrastructure.ai_gateway_factory import create_ai_gateway
from app.infrastructure.mock_ai_gateway import MockAIGateway
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


if __name__ == "__main__":
    unittest.main()
