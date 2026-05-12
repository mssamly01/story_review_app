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
        super().__init__("Tập truyện (Episodes)", parent)
        self.callbacks = callbacks or {}
        self.episode_list = QListWidget()
        self.title_edit = QLineEdit("Tập 1")
        self.tone_combo = QComboBox()
        self.tone_combo.addItems(["Bí ẩn", "Kịch tính", "Trung lập", "Hài hước", "Nhanh"])
        self._tone_map = {
            "Bí ẩn": "mysterious",
            "Kịch tính": "dramatic",
            "Trung lập": "neutral",
            "Hài hước": "humorous",
            "Nhanh": "fast-paced",
        }
        self.density_combo = QComboBox()
        self.density_combo.addItems(["Đầy đủ", "Cân bằng", "Tóm gọn"])
        self._density_map = {
            "Đầy đủ": "full",
            "Cân bằng": "balanced",
            "Tóm gọn": "condensed",
        }
        self.ai_mode_combo = QComboBox()
        self.ai_mode_combo.addItems(["quy tắc (deterministic)", "giả lập (mock)", "thật (real)"])
        self._ai_mode_map = {
            "quy tắc (deterministic)": "deterministic",
            "giả lập (mock)": "mock",
            "thật (real)": "real",
        }
        self.model_edit = QLineEdit()
        self.style_preset_edit = QLineEdit()

        layout = QGridLayout(self)
        layout.addWidget(self.episode_list, 0, 0, 8, 1)
        layout.addWidget(QLabel("Tiêu đề"), 0, 1)
        layout.addWidget(self.title_edit, 0, 2)
        layout.addWidget(QLabel("Phong cách (Tone)"), 1, 1)
        layout.addWidget(self.tone_combo, 1, 2)
        layout.addWidget(QLabel("Độ chi tiết (Density)"), 2, 1)
        layout.addWidget(self.density_combo, 2, 2)
        layout.addWidget(QLabel("Chế độ AI"), 3, 1)
        layout.addWidget(self.ai_mode_combo, 3, 2)
        layout.addWidget(QLabel("Model"), 4, 1)
        layout.addWidget(self.model_edit, 4, 2)
        layout.addWidget(QLabel("Style Preset"), 5, 1)
        layout.addWidget(self.style_preset_edit, 5, 2)

        plan_button = QPushButton("Lập kế hoạch tập")
        plan_button.clicked.connect(self._call("plan_episode"))
        layout.addWidget(plan_button, 6, 1, 1, 2)

        pipeline_button = QPushButton("Chạy toàn bộ Pipeline")
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
        tone_text = self.tone_combo.currentText()
        density_text = self.density_combo.currentText()
        ai_mode_text = self.ai_mode_combo.currentText()
        return {
            "episode_title": self.title_edit.text().strip() or "Tập 1",
            "tone": self._tone_map.get(tone_text, tone_text),
            "density": self._density_map.get(density_text, density_text),
            "ai_mode": self._ai_mode_map.get(ai_mode_text, ai_mode_text),
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
