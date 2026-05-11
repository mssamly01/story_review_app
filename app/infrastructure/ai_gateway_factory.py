"""Factory for AI gateway implementations.

Routing rules:

* ``mock_ai=True`` → :class:`MockAIGateway`, no provider lookup.
* ``real_ai=True`` → resolve the provider (explicit arg, ``--provider`` CLI
  flag, or ``AI_PROVIDER`` env var) and return the matching real gateway.
* Default provider is ``openai`` for backwards compatibility — existing
  scripts that don't pass ``provider=`` keep talking to OpenAI.
"""

from __future__ import annotations

import os

from app.infrastructure.ai_gateway import AIGateway
from app.infrastructure.mock_ai_gateway import MockAIGateway

DEFAULT_PROVIDER = "openai"
SUPPORTED_PROVIDERS = ("openai", "anthropic", "gemini", "ollama")


def create_ai_gateway(
    use_ai: bool,
    mock_ai: bool = False,
    real_ai: bool = False,
    model: str | None = None,
    provider: str | None = None,
) -> AIGateway | None:
    if not use_ai:
        return None
    if mock_ai and real_ai:
        raise ValueError("Choose either --mock-ai or --real-ai, not both.")
    if mock_ai:
        return MockAIGateway()
    if real_ai:
        return _build_real_gateway(provider, model)
    raise ValueError("AI mode requires either --mock-ai or --real-ai.")


def _build_real_gateway(provider: str | None, model: str | None) -> AIGateway:
    resolved = (provider or os.environ.get("AI_PROVIDER") or DEFAULT_PROVIDER).lower()

    if resolved == "openai":
        from app.infrastructure.openai_ai_gateway import OpenAIAIGateway

        return OpenAIAIGateway(model=model)
    if resolved == "anthropic":
        from app.infrastructure.anthropic_ai_gateway import AnthropicAIGateway

        return AnthropicAIGateway(model=model)
    if resolved == "gemini":
        from app.infrastructure.gemini_ai_gateway import GeminiAIGateway

        return GeminiAIGateway(model=model)
    if resolved == "ollama":
        from app.infrastructure.ollama_ai_gateway import OllamaAIGateway

        return OllamaAIGateway(model=model)

    raise ValueError(
        f"Unsupported AI provider: {resolved!r}. "
        f"Supported providers: {', '.join(SUPPORTED_PROVIDERS)}."
    )
