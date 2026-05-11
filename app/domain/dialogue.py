"""Dialogue domain model.

A ``Dialogue`` is one line spoken / thought / narrated inside a ``Beat``.
Introduced in project schema v3 as the first piece of the Novel-to-Comic
direction (định vị B): beats now carry both visual prompts AND the
character speech that should appear in speech bubbles / captions in the
rendered panel.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DIALOGUE_STYLES = ("speech", "thought", "shout", "whisper", "narration")
"""All currently-recognized dialogue styles.

These map to bubble shapes the renderer (or external comic letterer) is
expected to draw:

- ``speech``    — normal rounded speech bubble (default)
- ``thought``   — cloud bubble
- ``shout``     — jagged / spiky bubble
- ``whisper``   — dashed-outline bubble
- ``narration`` — rectangular caption box, no tail
"""

DEFAULT_DIALOGUE_STYLE = "speech"


@dataclass(slots=True)
class Dialogue:
    """One line of dialogue / thought / narration attached to a Beat.

    Attributes:
        speaker_id: ``character_id`` of the speaker. Use ``""`` (empty)
            when ``style == "narration"`` (off-screen narrator).
        line: The actual text content, in the project's language (vi).
        style: One of :data:`DIALOGUE_STYLES`. Defaults to ``"speech"``.
    """

    speaker_id: str
    line: str
    style: str = DEFAULT_DIALOGUE_STYLE

    def to_dict(self) -> dict[str, Any]:
        return {
            "speaker_id": self.speaker_id,
            "line": self.line,
            "style": self.style,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Dialogue":
        style = str(data.get("style", DEFAULT_DIALOGUE_STYLE)) or DEFAULT_DIALOGUE_STYLE
        return cls(
            speaker_id=str(data.get("speaker_id", "")),
            line=str(data.get("line", "")),
            style=style,
        )
