"""Project controls for the Tkinter UI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ProjectPanel(ttk.LabelFrame):
    def __init__(self, master: tk.Misc, callbacks: dict[str, object]) -> None:
        super().__init__(master, text="Project")
        self.callbacks = callbacks
        self.title_var = tk.StringVar(value="Untitled Project")
        self.path_var = tk.StringVar(value="")

        ttk.Label(self, text="Title").grid(row=0, column=0, sticky="w")
        ttk.Entry(self, textvariable=self.title_var, width=32).grid(
            row=0, column=1, columnspan=3, sticky="ew", padx=4
        )
        ttk.Button(self, text="New", command=self._call("new_project")).grid(
            row=1, column=0, sticky="ew", padx=2, pady=2
        )
        ttk.Button(self, text="Open", command=self._call("open_project")).grid(
            row=1, column=1, sticky="ew", padx=2, pady=2
        )
        ttk.Button(self, text="Save", command=self._call("save_project")).grid(
            row=1, column=2, sticky="ew", padx=2, pady=2
        )
        ttk.Button(self, text="Save As", command=self._call("save_project_as")).grid(
            row=1, column=3, sticky="ew", padx=2, pady=2
        )
        ttk.Label(self, textvariable=self.path_var).grid(
            row=2, column=0, columnspan=4, sticky="w"
        )
        self.columnconfigure(1, weight=1)

    def set_project_info(self, title: str, path: str = "") -> None:
        self.title_var.set(title)
        self.path_var.set(path)

    def _call(self, name: str):
        def callback() -> None:
            handler = self.callbacks.get(name)
            if callable(handler):
                handler()

        return callback

