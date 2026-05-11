"""Factory for optional AI gateway implementations."""

from __future__ import annotations

from app.infrastructure.ai_gateway import AIGateway
from app.infrastructure.mock_ai_gateway import MockAIGateway
from app.infrastructure.openai_ai_gateway import OpenAIAIGateway


def create_ai_gateway(
    use_ai: bool,
    mock_ai: bool = False,
    real_ai: bool = False,
    model: str | None = None,
) -> AIGateway | None:
    if not use_ai:
        return None
    if mock_ai and real_ai:
        raise ValueError("Choose either --mock-ai or --real-ai, not both.")
    if mock_ai:
        return MockAIGateway()
    if real_ai:
        return OpenAIAIGateway(model=model)
    raise ValueError("AI mode requires either --mock-ai or --real-ai.")
