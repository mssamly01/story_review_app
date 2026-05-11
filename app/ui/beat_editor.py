"""PySide6 beat editor for structured beat fields."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QWidget,
)


class BeatEditor(QGroupBox):
    MULTILINE_FIELDS = {
        "review_text",
        "visual_description",
        "image_prompt",
        "negative_prompt",
    }
    FIELD_NAMES = [
        "review_text",
        "visual_description",
        "image_prompt",
        "negative_prompt",
        "characters",
        "location",
        "emotion",
        "shot_type",
        "continuity_tags",
    ]
    FIELD_LABELS = {
        "review_text": "Nội dung Review",
        "visual_description": "Mô tả hình ảnh",
        "image_prompt": "Image Prompt",
        "negative_prompt": "Negative Prompt",
        "characters": "Nhân vật",
        "location": "Bối cảnh",
        "emotion": "Cảm xúc",
        "shot_type": "Góc máy",
        "continuity_tags": "Thẻ liên kết (Continuity)",
    }

    def __init__(
        self,
        parent: QWidget | None = None,
        callbacks: dict[str, Callable[..., Any]] | None = None,
    ) -> None:
        super().__init__("Chỉnh sửa Nhịp (Beat Editor)", parent)
        self.callbacks = callbacks or {}
        self._beat_id: str | None = None
        self.fields: dict[str, QLineEdit | QPlainTextEdit] = {}

        layout = QGridLayout(self)
        for row, name in enumerate(self.FIELD_NAMES):
            label_text = self.FIELD_LABELS.get(name, name.replace("_", " ").title())
            label = QLabel(label_text)
            layout.addWidget(label, row, 0)
            if name in self.MULTILINE_FIELDS:
                widget = QPlainTextEdit()
                widget.setMaximumBlockCount(5000)
                layout.addWidget(widget, row, 1)
            else:
                widget = QLineEdit()
                layout.addWidget(widget, row, 1)
            self.fields[name] = widget

        apply_button = QPushButton("Cập nhật nhịp")
        apply_button.clicked.connect(self._apply)
        layout.addWidget(apply_button, len(self.FIELD_NAMES), 0, 1, 2)
        layout.setColumnStretch(1, 1)

    def set_beat(self, beat) -> None:
        self._beat_id = beat.beat_id
        for name in self.FIELD_NAMES:
            value = getattr(beat, name)
            display_value = ", ".join(value) if isinstance(value, list) else str(value)
            widget = self.fields[name]
            if isinstance(widget, QPlainTextEdit):
                widget.setPlainText(display_value)
            else:
                widget.setText(display_value)

    def clear(self) -> None:
        self._beat_id = None
        for widget in self.fields.values():
            if isinstance(widget, QPlainTextEdit):
                widget.clear()
            else:
                widget.setText("")

    def values(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for name, widget in self.fields.items():
            if isinstance(widget, QPlainTextEdit):
                result[name] = widget.toPlainText()
            else:
                result[name] = widget.text()
        return result

    def _apply(self) -> None:
        handler = self.callbacks.get("update_beat")
        if self._beat_id and callable(handler):
            handler(self._beat_id, self.values())
