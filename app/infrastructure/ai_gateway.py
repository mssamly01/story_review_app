"""AI gateway contract for generation services."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AIGateway(Protocol):
    def generate_text(
        self,
        prompt_name: str,
        input_data: dict[str, Any],
        system_message: str | None = None,
    ) -> str:
        """Generate deterministic or provider-backed text for a prompt."""

    def generate_json(
        self,
        prompt_name: str,
        input_data: dict[str, Any],
        system_message: str | None = None,
    ) -> dict[str, Any]:
        """Generate structured JSON data for a prompt."""
