"""Source chapter panel for the Tkinter UI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class SourceChapterPanel(ttk.LabelFrame):
    def __init__(self, master: tk.Misc, callbacks: dict[str, object]) -> None:
        super().__init__(master, text="Source Chapters")
        self.callbacks = callbacks
        self.title_var = tk.StringVar()
        self.number_var = tk.StringVar(value="1")
        self.chapter_list = tk.Listbox(self, height=6, exportselection=False)
        self.raw_text = tk.Text(self, height=12, wrap="word")

        self.chapter_list.grid(row=0, column=0, rowspan=5, sticky="nsew", padx=3)
        self.chapter_list.bind("<<ListboxSelect>>", self._on_select)
        ttk.Label(self, text="Title").grid(row=0, column=1, sticky="w")
        ttk.Entry(self, textvariable=self.title_var).grid(row=0, column=2, sticky="ew")
        ttk.Label(self, text="Number").grid(row=1, column=1, sticky="w")
        ttk.Entry(self, textvariable=self.number_var, width=8).grid(
            row=1, column=2, sticky="w"
        )
        ttk.Button(self, text="Add From File", command=self._call("add_chapter")).grid(
            row=2, column=1, columnspan=2, sticky="ew", pady=2
        )
        ttk.Button(self, text="Apply Source Edits", command=self._apply_edits).grid(
            row=3, column=1, columnspan=2, sticky="ew", pady=2
        )
        self.raw_text.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=3)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(2, weight=1)
        self.rowconfigure(5, weight=1)
        self._chapter_ids: list[str] = []

    def set_chapters(self, chapters) -> None:
        self._chapter_ids = [chapter.chapter_id for chapter in chapters]
        self.chapter_list.delete(0, tk.END)
        for chapter in chapters:
            self.chapter_list.insert(
                tk.END,
                f"{chapter.chapter_id} | {chapter.chapter_number} | {chapter.title}",
            )

    def set_current_chapter(self, chapter) -> None:
        self.title_var.set(chapter.title)
        self.number_var.set(str(chapter.chapter_number))
        self.raw_text.delete("1.0", tk.END)
        self.raw_text.insert("1.0", chapter.raw_text)

    def selected_chapter_id(self) -> str | None:
        selected = self.chapter_list.curselection()
        if not selected:
            return None
        return self._chapter_ids[selected[0]]

    def edited_values(self) -> dict[str, object]:
        return {
            "title": self.title_var.get(),
            "chapter_number": int(self.number_var.get()),
            "raw_text": self.raw_text.get("1.0", "end-1c"),
        }

    def _on_select(self, event: object) -> None:
        chapter_id = self.selected_chapter_id()
        handler = self.callbacks.get("select_chapter")
        if chapter_id and callable(handler):
            handler(chapter_id)

    def _apply_edits(self) -> None:
        chapter_id = self.selected_chapter_id()
        handler = self.callbacks.get("update_chapter")
        if chapter_id and callable(handler):
            handler(chapter_id, self.edited_values())

    def _call(self, name: str):
        def callback() -> None:
            handler = self.callbacks.get(name)
            if callable(handler):
                handler()

        return callback

