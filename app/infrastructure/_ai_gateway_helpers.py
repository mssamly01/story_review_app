"""Shared helpers and types for concrete ``AIGateway`` implementations.

All real-provider gateways (OpenAI, Anthropic, Gemini, Ollama) share the same
prompt-building convention, the same JSON-parsing rules, and the same token
accounting shape. Putting that in one module keeps the providers consistent
and makes it cheap to add a new one.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable


class AIConfigurationError(RuntimeError):
    """Raised when a real AI provider is requested but not configured."""


class AIResponseParseError(ValueError):
    """Raised when model output cannot be parsed into the expected structure."""


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Token counters reported by the provider for a single call."""

    prompt_name: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int


TokenCallback = Callable[[TokenUsage], None]


def build_prompt(template: str, input_data: dict[str, Any]) -> str:
    """Render the user-facing prompt from a template + structured input.

    The structured input is serialized to indented JSON under a
    ``## Runtime input`` heading so models reliably read it back.
    """
    payload = json.dumps(
        input_data,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    return f"{template.rstrip()}\n\n## Runtime input\n```json\n{payload}\n```"


def strip_json_fence(text: str) -> str:
    """Strip a leading/trailing ```json ... ``` fence from model output."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def parse_json_response(
    text: str,
    prompt_name: str,
    provider_label: str = "AI",
) -> dict[str, Any]:
    """Parse ``text`` as JSON, raising :class:`AIResponseParseError` on failure.

    The ``provider_label`` (e.g. ``"OpenAI"``, ``"Anthropic"``) is interpolated
    into the error message so failures point at the right provider in logs.
    """
    cleaned = strip_json_fence(text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AIResponseParseError(
            f"{provider_label} response for '{prompt_name}' was not valid JSON."
        ) from exc

    if not isinstance(data, dict):
        raise AIResponseParseError(
            f"{provider_label} response for '{prompt_name}' must be a JSON object."
        )
    return data
