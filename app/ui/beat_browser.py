"""Scene and beat browser for the Tkinter UI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class BeatBrowser(ttk.LabelFrame):
    def __init__(self, master: tk.Misc, callbacks: dict[str, object]) -> None:
        super().__init__(master, text="Scenes and Beats")
        self.callbacks = callbacks
        self.scene_list = tk.Listbox(self, height=5, exportselection=False)
        self.beat_list = tk.Listbox(self, height=8, exportselection=False)
        self._scene_ids: list[str] = []
        self._beat_ids: list[str] = []

        ttk.Label(self, text="Scenes").grid(row=0, column=0, sticky="w")
        ttk.Label(self, text="Beats").grid(row=0, column=1, sticky="w")
        self.scene_list.grid(row=1, column=0, sticky="nsew", padx=3)
        self.beat_list.grid(row=1, column=1, sticky="nsew", padx=3)
        self.scene_list.bind("<<ListboxSelect>>", self._on_scene_select)
        self.beat_list.bind("<<ListboxSelect>>", self._on_beat_select)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

    def set_scenes(self, scenes) -> None:
        self._scene_ids = [scene.scene_id for scene in scenes]
        self.scene_list.delete(0, tk.END)
        for scene in scenes:
            self.scene_list.insert(tk.END, f"{scene.scene_id} | {scene.title}")
        self.set_beats([])

    def set_beats(self, beats) -> None:
        self._beat_ids = [beat.beat_id for beat in beats]
        self.beat_list.delete(0, tk.END)
        for beat in beats:
            preview = beat.review_text or beat.action
            if len(preview) > 60:
                preview = preview[:57] + "..."
            self.beat_list.insert(
                tk.END,
                f"{beat.beat_id} | {beat.order_index} | {beat.story_function} | {preview}",
            )

    def selected_scene_id(self) -> str | None:
        selected = self.scene_list.curselection()
        if not selected:
            return None
        return self._scene_ids[selected[0]]

    def selected_beat_id(self) -> str | None:
        selected = self.beat_list.curselection()
        if not selected:
            return None
        return self._beat_ids[selected[0]]

    def _on_scene_select(self, event: object) -> None:
        scene_id = self.selected_scene_id()
        handler = self.callbacks.get("select_scene")
        if scene_id and callable(handler):
            handler(scene_id)

    def _on_beat_select(self, event: object) -> None:
        beat_id = self.selected_beat_id()
        handler = self.callbacks.get("select_beat")
        if beat_id and callable(handler):
            handler(beat_id)

