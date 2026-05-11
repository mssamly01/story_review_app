"""Optional OpenAI-backed implementation of the AI gateway."""

from __future__ import annotations

import json
import os
from typing import Any

from app.infrastructure.ai_gateway import AIGateway
from app.infrastructure.prompt_template_loader import PromptTemplateLoader


class AIConfigurationError(RuntimeError):
    """Raised when a real AI provider is requested but not configured."""


class AIResponseParseError(ValueError):
    """Raised when model output cannot be parsed into the expected structure."""


class OpenAIAIGateway(AIGateway):
    DEFAULT_MODEL = "gpt-4.1-mini"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        prompt_loader: PromptTemplateLoader | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise AIConfigurationError(
                "Real AI mode requires an OpenAI API key. "
                "Pass one explicitly or set OPENAI_API_KEY."
            )

        self.model = model or os.environ.get("OPENAI_MODEL") or self.DEFAULT_MODEL
        self.prompt_loader = prompt_loader or PromptTemplateLoader()

    def generate_text(
        self,
        prompt_name: str,
        input_data: dict[str, Any],
        system_message: str | None = None,
    ) -> str:
        template = self.prompt_loader.load(prompt_name)
        prompt = self._build_prompt(template, input_data)
        return self._call_model(prompt, system_message)

    def generate_json(
        self,
        prompt_name: str,
        input_data: dict[str, Any],
        system_message: str | None = None,
    ) -> dict[str, Any]:
        text = self.generate_text(prompt_name, input_data, system_message)
        return self._parse_json(text, prompt_name)

    def _build_prompt(self, template: str, input_data: dict[str, Any]) -> str:
        payload = json.dumps(
            input_data,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        return f"{template.rstrip()}\n\n## Runtime input\n```json\n{payload}\n```"

    def _call_model(self, prompt: str, system_message: str | None) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise AIConfigurationError(
                "Real AI mode requires the optional OpenAI Python package."
            ) from exc

        client = OpenAI(api_key=self.api_key)
        messages: list[dict[str, str]] = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        response = client.responses.create(
            model=self.model,
            input=messages,
        )
        return self._extract_text(response)

    def _extract_text(self, response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        if isinstance(response, dict):
            output_text = response.get("output_text")
            if isinstance(output_text, str) and output_text.strip():
                return output_text
            choices = response.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content")
                if isinstance(content, str) and content.strip():
                    return content

        choices = getattr(response, "choices", None)
        if choices:
            message = getattr(choices[0], "message", None)
            content = getattr(message, "content", None)
            if isinstance(content, str) and content.strip():
                return content

        raise AIResponseParseError("OpenAI response did not contain text output.")

    def _parse_json(self, text: str, prompt_name: str) -> dict[str, Any]:
        cleaned = self._strip_json_fence(text)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise AIResponseParseError(
                f"OpenAI response for '{prompt_name}' was not valid JSON."
            ) from exc

        if not isinstance(data, dict):
            raise AIResponseParseError(
                f"OpenAI response for '{prompt_name}' must be a JSON object."
            )
        return data

    def _strip_json_fence(self, text: str) -> str:
        stripped = text.strip()
        if not stripped.startswith("```"):
            return stripped

        lines = stripped.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
