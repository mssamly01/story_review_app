"""PySide6 export and profile controls."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QWidget,
)


ITEM_ROLE = Qt.ItemDataRole.UserRole


class ExportPanel(QGroupBox):
    def __init__(
        self,
        parent: QWidget | None = None,
        callbacks: dict[str, Callable[..., Any]] | None = None,
    ) -> None:
        super().__init__("Xuất bản (Export)", parent)
        self.callbacks = callbacks or {}
        self.format_combo = QComboBox()
        self.format_combo.addItems(
            ["markdown", "json", "csv", "review-txt", "prompts-txt"]
        )
        self.profile_combo = QComboBox()

        layout = QGridLayout(self)
        layout.addWidget(QLabel("Định dạng"), 0, 0)
        layout.addWidget(self.format_combo, 0, 1)
        export_button = QPushButton("Xuất tập")
        export_button.clicked.connect(self._export)
        layout.addWidget(export_button, 0, 2)

        layout.addWidget(QLabel("Profile"), 1, 0)
        layout.addWidget(self.profile_combo, 1, 1)
        profile_button = QPushButton("Xuất Profile")
        profile_button.clicked.connect(self._export_profile)
        layout.addWidget(profile_button, 1, 2)
        layout.setColumnStretch(1, 1)

    def set_profiles(self, profiles) -> None:
        self.profile_combo.clear()
        for profile in profiles:
            self.profile_combo.addItem(profile.name, profile.profile_id)

    def selected_profile_id(self) -> str | None:
        index = self.profile_combo.currentIndex()
        if index < 0:
            return None
        return self.profile_combo.itemData(index, ITEM_ROLE)

    def _export(self) -> None:
        handler = self.callbacks.get("export_episode")
        if callable(handler):
            handler(self.format_combo.currentText())

    def _export_profile(self) -> None:
        handler = self.callbacks.get("export_profile")
        profile_id = self.selected_profile_id()
        if profile_id and callable(handler):
            handler(profile_id)
