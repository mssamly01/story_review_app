"""PySide6 source chapter panel."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)


ITEM_ROLE = Qt.ItemDataRole.UserRole


class SourceChapterPanel(QGroupBox):
    def __init__(
        self,
        parent: QWidget | None = None,
        callbacks: dict[str, Callable[..., Any]] | None = None,
    ) -> None:
        super().__init__("Source Chapters", parent)
        self.callbacks = callbacks or {}
        self.chapter_list = QListWidget()
        self.title_edit = QLineEdit()
        self.number_spin = QSpinBox()
        self.number_spin.setRange(1, 9999)
        self.raw_text_edit = QPlainTextEdit()

        layout = QGridLayout(self)
        layout.addWidget(self.chapter_list, 0, 0, 5, 1)
        layout.addWidget(QLabel("Title"), 0, 1)
        layout.addWidget(self.title_edit, 0, 2)
        layout.addWidget(QLabel("Number"), 1, 1)
        layout.addWidget(self.number_spin, 1, 2)

        add_button = QPushButton("Add From File")
        add_button.clicked.connect(self._call("add_chapter"))
        layout.addWidget(add_button, 2, 1, 1, 2)

        apply_button = QPushButton("Apply Source Edits")
        apply_button.clicked.connect(self._apply_edits)
        layout.addWidget(apply_button, 3, 1, 1, 2)

        layout.addWidget(self.raw_text_edit, 5, 0, 1, 3)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(2, 1)
        layout.setRowStretch(5, 1)

        self.chapter_list.currentItemChanged.connect(self._on_select)

    def set_chapters(self, chapters) -> None:
        self.chapter_list.clear()
        for chapter in chapters:
            item = QListWidgetItem(
                f"{chapter.chapter_id} | {chapter.chapter_number} | {chapter.title}"
            )
            item.setData(ITEM_ROLE, chapter.chapter_id)
            self.chapter_list.addItem(item)

    def set_current_chapter(self, chapter) -> None:
        self.title_edit.setText(chapter.title)
        self.number_spin.setValue(int(chapter.chapter_number))
        self.raw_text_edit.setPlainText(chapter.raw_text)

    def selected_chapter_id(self) -> str | None:
        item = self.chapter_list.currentItem()
        if item is None:
            return None
        return item.data(ITEM_ROLE)

    def edited_values(self) -> dict[str, object]:
        return {
            "title": self.title_edit.text(),
            "chapter_number": int(self.number_spin.value()),
            "raw_text": self.raw_text_edit.toPlainText(),
        }

    def _on_select(self, current: QListWidgetItem | None, previous: object) -> None:
        if current is None:
            return
        handler = self.callbacks.get("select_chapter")
        if callable(handler):
            handler(current.data(ITEM_ROLE))

    def _apply_edits(self) -> None:
        chapter_id = self.selected_chapter_id()
        handler = self.callbacks.get("update_chapter")
        if chapter_id and callable(handler):
            handler(chapter_id, self.edited_values())

    def _call(self, name: str) -> Callable[[], None]:
        def callback() -> None:
            handler = self.callbacks.get(name)
            if callable(handler):
                handler()

        return callback
