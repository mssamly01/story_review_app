"""PySide6 project controls for the desktop UI."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)


class ProjectPanel(QGroupBox):
    def __init__(
        self,
        parent: QWidget | None = None,
        callbacks: dict[str, Callable[..., Any]] | None = None,
    ) -> None:
        super().__init__("Dự án", parent)
        self.callbacks = callbacks or {}
        self.title_edit = QLineEdit("Dự án không tên")
        self.path_label = QLabel("")
        self.path_label.setWordWrap(True)

        layout = QGridLayout(self)
        layout.addWidget(QLabel("Tiêu đề"), 0, 0)
        layout.addWidget(self.title_edit, 0, 1, 1, 4)

        buttons = [
            ("Mới", "new_project"),
            ("Mở", "open_project"),
            ("Lưu", "save_project"),
            ("Lưu mới", "save_project_as"),
        ]
        for column, (label, callback_name) in enumerate(buttons):
            button = QPushButton(label)
            button.clicked.connect(self._call(callback_name))
            layout.addWidget(button, 1, column)

        layout.addWidget(self.path_label, 2, 0, 1, 5)
        layout.setColumnStretch(4, 1)

    def project_title(self) -> str:
        return self.title_edit.text().strip()

    def set_project_info(self, title: str, path: str = "") -> None:
        self.title_edit.setText(title)
        self.path_label.setText(path)

    def _call(self, name: str) -> Callable[[], None]:
        def callback() -> None:
            handler = self.callbacks.get(name)
            if callable(handler):
                handler()

        return callback
