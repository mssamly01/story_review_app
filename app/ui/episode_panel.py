"""PySide6 episode controls."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QWidget,
)


ITEM_ROLE = Qt.ItemDataRole.UserRole


class EpisodePanel(QGroupBox):
    def __init__(
        self,
        parent: QWidget | None = None,
        callbacks: dict[str, Callable[..., Any]] | None = None,
    ) -> None:
        super().__init__("Episodes", parent)
        self.callbacks = callbacks or {}
        self.episode_list = QListWidget()
        self.title_edit = QLineEdit("Episode 1")
        self.tone_combo = QComboBox()
        self.tone_combo.addItems(
            ["mysterious", "dramatic", "neutral", "humorous", "fast-paced"]
        )
        self.density_combo = QComboBox()
        self.density_combo.addItems(["full", "balanced", "condensed"])
        self.ai_mode_combo = QComboBox()
        self.ai_mode_combo.addItems(["deterministic", "mock", "real"])
        self.model_edit = QLineEdit()
        self.style_preset_edit = QLineEdit()

        layout = QGridLayout(self)
        layout.addWidget(self.episode_list, 0, 0, 8, 1)
        layout.addWidget(QLabel("Title"), 0, 1)
        layout.addWidget(self.title_edit, 0, 2)
        layout.addWidget(QLabel("Tone"), 1, 1)
        layout.addWidget(self.tone_combo, 1, 2)
        layout.addWidget(QLabel("Density"), 2, 1)
        layout.addWidget(self.density_combo, 2, 2)
        layout.addWidget(QLabel("AI Mode"), 3, 1)
        layout.addWidget(self.ai_mode_combo, 3, 2)
        layout.addWidget(QLabel("Model"), 4, 1)
        layout.addWidget(self.model_edit, 4, 2)
        layout.addWidget(QLabel("Style Preset"), 5, 1)
        layout.addWidget(self.style_preset_edit, 5, 2)

        plan_button = QPushButton("Plan Episode")
        plan_button.clicked.connect(self._call("plan_episode"))
        layout.addWidget(plan_button, 6, 1, 1, 2)

        pipeline_button = QPushButton("Full Pipeline")
        pipeline_button.clicked.connect(self._call("run_pipeline"))
        layout.addWidget(pipeline_button, 7, 1, 1, 2)

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(2, 1)
        self.episode_list.currentItemChanged.connect(self._on_select)

    def set_episodes(self, episodes) -> None:
        self.episode_list.clear()
        for episode in episodes:
            item = QListWidgetItem(f"{episode.episode_id} | {episode.title}")
            item.setData(ITEM_ROLE, episode.episode_id)
            self.episode_list.addItem(item)

    def selected_episode_id(self) -> str | None:
        item = self.episode_list.currentItem()
        if item is None:
            return None
        return item.data(ITEM_ROLE)

    def settings(self) -> dict[str, str | None]:
        return {
            "episode_title": self.title_edit.text().strip() or "Episode 1",
            "tone": self.tone_combo.currentText(),
            "density": self.density_combo.currentText(),
            "ai_mode": self.ai_mode_combo.currentText(),
            "model": self.model_edit.text().strip() or None,
            "style_preset_id": self.style_preset_edit.text().strip() or None,
        }

    def _on_select(self, current: QListWidgetItem | None, previous: object) -> None:
        if current is None:
            return
        handler = self.callbacks.get("select_episode")
        if callable(handler):
            handler(current.data(ITEM_ROLE))

    def _call(self, name: str) -> Callable[[], None]:
        def callback() -> None:
            handler = self.callbacks.get(name)
            if callable(handler):
                handler()

        return callback
