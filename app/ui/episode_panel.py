"""Episode controls for the Tkinter UI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class EpisodePanel(ttk.LabelFrame):
    def __init__(self, master: tk.Misc, callbacks: dict[str, object]) -> None:
        super().__init__(master, text="Episodes")
        self.callbacks = callbacks
        self.title_var = tk.StringVar(value="Episode 1")
        self.tone_var = tk.StringVar(value="mysterious")
        self.density_var = tk.StringVar(value="full")
        self.ai_mode_var = tk.StringVar(value="deterministic")
        self.model_var = tk.StringVar(value="")
        self.episode_list = tk.Listbox(self, height=6, exportselection=False)
        self._episode_ids: list[str] = []

        self.episode_list.grid(row=0, column=0, rowspan=7, sticky="nsew", padx=3)
        self.episode_list.bind("<<ListboxSelect>>", self._on_select)
        ttk.Label(self, text="Title").grid(row=0, column=1, sticky="w")
        ttk.Entry(self, textvariable=self.title_var).grid(row=0, column=2, sticky="ew")
        ttk.Label(self, text="Tone").grid(row=1, column=1, sticky="w")
        ttk.Combobox(
            self,
            textvariable=self.tone_var,
            values=["mysterious", "dramatic", "neutral", "humorous", "fast-paced"],
            state="readonly",
        ).grid(row=1, column=2, sticky="ew")
        ttk.Label(self, text="Density").grid(row=2, column=1, sticky="w")
        ttk.Combobox(
            self,
            textvariable=self.density_var,
            values=["full", "balanced", "condensed"],
            state="readonly",
        ).grid(row=2, column=2, sticky="ew")
        ttk.Label(self, text="AI Mode").grid(row=3, column=1, sticky="w")
        ttk.Combobox(
            self,
            textvariable=self.ai_mode_var,
            values=["deterministic", "mock", "real"],
            state="readonly",
        ).grid(row=3, column=2, sticky="ew")
        ttk.Label(self, text="Model").grid(row=4, column=1, sticky="w")
        ttk.Entry(self, textvariable=self.model_var).grid(row=4, column=2, sticky="ew")
        ttk.Button(self, text="Plan Episode", command=self._call("plan_episode")).grid(
            row=5, column=1, columnspan=2, sticky="ew", pady=2
        )
        ttk.Button(self, text="Full Pipeline", command=self._call("run_pipeline")).grid(
            row=6, column=1, columnspan=2, sticky="ew", pady=2
        )
        self.columnconfigure(0, weight=1)
        self.columnconfigure(2, weight=1)

    def set_episodes(self, episodes) -> None:
        self._episode_ids = [episode.episode_id for episode in episodes]
        self.episode_list.delete(0, tk.END)
        for episode in episodes:
            self.episode_list.insert(tk.END, f"{episode.episode_id} | {episode.title}")

    def selected_episode_id(self) -> str | None:
        selected = self.episode_list.curselection()
        if not selected:
            return None
        return self._episode_ids[selected[0]]

    def settings(self) -> dict[str, str]:
        return {
            "episode_title": self.title_var.get(),
            "tone": self.tone_var.get(),
            "density": self.density_var.get(),
            "ai_mode": self.ai_mode_var.get(),
            "model": self.model_var.get() or None,
        }

    def _on_select(self, event: object) -> None:
        episode_id = self.selected_episode_id()
        handler = self.callbacks.get("select_episode")
        if episode_id and callable(handler):
            handler(episode_id)

    def _call(self, name: str):
        def callback() -> None:
            handler = self.callbacks.get(name)
            if callable(handler):
                handler()

        return callback

