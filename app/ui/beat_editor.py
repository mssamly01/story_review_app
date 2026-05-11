"""Beat editor for structured beat fields."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class BeatEditor(ttk.LabelFrame):
    FIELD_NAMES = [
        "review_text",
        "visual_description",
        "image_prompt",
        "negative_prompt",
        "characters",
        "location",
        "emotion",
        "shot_type",
        "continuity_tags",
    ]

    def __init__(self, master: tk.Misc, callbacks: dict[str, object]) -> None:
        super().__init__(master, text="Beat Editor")
        self.callbacks = callbacks
        self._beat_id: str | None = None
        self.fields: dict[str, tk.Text | tk.StringVar] = {}

        row = 0
        for name in self.FIELD_NAMES:
            ttk.Label(self, text=name.replace("_", " ").title()).grid(
                row=row, column=0, sticky="nw"
            )
            if name in {
                "review_text",
                "visual_description",
                "image_prompt",
                "negative_prompt",
            }:
                widget = tk.Text(self, height=3, wrap="word")
                widget.grid(row=row, column=1, sticky="ew", pady=2)
                self.fields[name] = widget
            else:
                value = tk.StringVar()
                ttk.Entry(self, textvariable=value).grid(row=row, column=1, sticky="ew")
                self.fields[name] = value
            row += 1

        ttk.Button(self, text="Apply Beat Edits", command=self._apply).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=4
        )
        self.columnconfigure(1, weight=1)

    def set_beat(self, beat) -> None:
        self._beat_id = beat.beat_id
        for name in self.FIELD_NAMES:
            value = getattr(beat, name)
            if isinstance(value, list):
                display_value = ", ".join(value)
            else:
                display_value = value
            widget = self.fields[name]
            if isinstance(widget, tk.Text):
                widget.delete("1.0", tk.END)
                widget.insert("1.0", display_value)
            else:
                widget.set(display_value)

    def values(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for name, widget in self.fields.items():
            if isinstance(widget, tk.Text):
                result[name] = widget.get("1.0", "end-1c")
            else:
                result[name] = widget.get()
        return result

    def _apply(self) -> None:
        handler = self.callbacks.get("update_beat")
        if self._beat_id and callable(handler):
            handler(self._beat_id, self.values())

