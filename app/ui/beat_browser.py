"""PySide6 scene and beat browser."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QWidget,
)

ITEM_ROLE = Qt.ItemDataRole.UserRole


class BeatBrowser(QGroupBox):
    def __init__(
        self,
        parent: QWidget | None = None,
        callbacks: dict[str, Callable[..., Any]] | None = None,
    ) -> None:
        super().__init__("Phân cảnh và Nhịp (Scenes & Beats)", parent)
        self.callbacks = callbacks or {}
        self.scene_list = QListWidget()
        self.beat_list = QListWidget()

        layout = QGridLayout(self)
        layout.addWidget(QLabel("Phân cảnh (Scenes)"), 0, 0)
        layout.addWidget(QLabel("Nhịp truyện (Beats)"), 0, 1)
        layout.addWidget(self.scene_list, 1, 0)
        layout.addWidget(self.beat_list, 1, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setRowStretch(1, 1)

        self.scene_list.currentItemChanged.connect(self._on_scene_select)
        self.beat_list.currentItemChanged.connect(self._on_beat_select)

    def set_scenes(self, scenes) -> None:
        self.scene_list.clear()
        for scene in scenes:
            item = QListWidgetItem(f"{scene.scene_id} | {scene.title}")
            item.setData(ITEM_ROLE, scene.scene_id)
            self.scene_list.addItem(item)
        self.set_beats([])

    def set_beats(self, beats) -> None:
        self.beat_list.clear()
        for beat in beats:
            preview = beat.review_text or beat.action
            if len(preview) > 70:
                preview = preview[:67] + "..."
            item = QListWidgetItem(
                f"{beat.beat_id} | {beat.order_index} | " f"{beat.story_function} | {preview}"
            )
            item.setData(ITEM_ROLE, beat.beat_id)
            self.beat_list.addItem(item)

    def selected_scene_id(self) -> str | None:
        item = self.scene_list.currentItem()
        if item is None:
            return None
        return item.data(ITEM_ROLE)

    def selected_beat_id(self) -> str | None:
        item = self.beat_list.currentItem()
        if item is None:
            return None
        return item.data(ITEM_ROLE)

    def _on_scene_select(self, current: QListWidgetItem | None, previous: object) -> None:
        if current is None:
            return
        handler = self.callbacks.get("select_scene")
        if callable(handler):
            handler(current.data(ITEM_ROLE))

    def _on_beat_select(self, current: QListWidgetItem | None, previous: object) -> None:
        if current is None:
            return
        handler = self.callbacks.get("select_beat")
        if callable(handler):
            handler(current.data(ITEM_ROLE))
