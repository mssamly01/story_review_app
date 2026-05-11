"""Export panel for the Tkinter UI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ExportPanel(ttk.LabelFrame):
    def __init__(self, master: tk.Misc, callbacks: dict[str, object]) -> None:
        super().__init__(master, text="Export")
        self.callbacks = callbacks
        self.format_var = tk.StringVar(value="markdown")
        ttk.Combobox(
            self,
            textvariable=self.format_var,
            values=["markdown", "json", "csv", "review-txt", "prompts-txt"],
            state="readonly",
        ).grid(row=0, column=0, sticky="ew", padx=3)
        ttk.Button(self, text="Export Episode", command=self._export).grid(
            row=0, column=1, sticky="ew", padx=3
        )
        self.columnconfigure(0, weight=1)

    def _export(self) -> None:
        handler = self.callbacks.get("export_episode")
        if callable(handler):
            handler(self.format_var.get())
