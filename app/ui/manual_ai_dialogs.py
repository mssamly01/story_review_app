"""Dialog windows for Manual AI workflow.

PromptExportDialog — shows prompt text, user copies to external AI.
ResultImportDialog — user pastes JSON result from external AI.
"""

from __future__ import annotations

import json
import re

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)


class PromptExportDialog(QDialog):
    """Read-only dialog showing prompt text with a Copy button."""

    def __init__(
        self,
        prompt_text: str,
        step_name: str = "",
        parent: object = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Lấy Prompt — {step_name}")
        self.resize(850, 600)
        self.prompt_text = prompt_text
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(
            QLabel(
                "Copy toàn bộ nội dung bên dưới → paste vào ChatGPT / Claude / Gemini.\n"
                "AI sẽ trả về JSON. Sau đó dùng nút 'Dán kết quả' để import."
            )
        )

        self.text_view = QPlainTextEdit()
        self.text_view.setPlainText(self.prompt_text)
        self.text_view.setReadOnly(True)
        layout.addWidget(self.text_view)

        btn_layout = QHBoxLayout()
        self.btn_copy = QPushButton("Copy vào Clipboard")
        self.btn_close = QPushButton("Đóng")
        btn_layout.addWidget(self.btn_copy)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)

        self.btn_copy.clicked.connect(self._on_copy)
        self.btn_close.clicked.connect(self.accept)

    def _on_copy(self) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self.prompt_text)
        self.btn_copy.setText("Đã copy!")


class ResultImportDialog(QDialog):
    """Dialog where user pastes JSON result from external AI."""

    def __init__(
        self,
        step_name: str = "",
        parent: object = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Dán kết quả AI — {step_name}")
        self.resize(850, 600)
        self.result_data: dict | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(
            QLabel(
                "Paste JSON kết quả từ AI vào ô bên dưới.\n"
                "Hỗ trợ JSON thuần hoặc JSON trong markdown code block (```json ... ```)."
            )
        )

        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText('Paste JSON tại đây...\n{\n  "scenes": [...]\n}')
        layout.addWidget(self.text_edit)

        btn_layout = QHBoxLayout()
        self.btn_paste = QPushButton("Paste từ Clipboard")
        self.btn_apply = QPushButton("Áp dụng kết quả")
        self.btn_cancel = QPushButton("Hủy")
        btn_layout.addWidget(self.btn_paste)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self.btn_paste.clicked.connect(self._on_paste)
        self.btn_apply.clicked.connect(self._on_apply)
        self.btn_cancel.clicked.connect(self.reject)

    def _on_paste(self) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            text = clipboard.text()
            if text:
                self.text_edit.setPlainText(text)

    def _on_apply(self) -> None:
        raw = self.text_edit.toPlainText().strip()
        if not raw:
            QMessageBox.warning(self, "Cảnh báo", "Chưa có dữ liệu JSON.")
            return

        cleaned = self._strip_markdown_code_block(raw)
        try:
            self.result_data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            QMessageBox.critical(
                self,
                "Lỗi JSON",
                f"Không thể parse JSON:\n{exc}",
            )
            return

        self.accept()

    @staticmethod
    def _strip_markdown_code_block(text: str) -> str:
        """Remove ```json ... ``` wrapper if present."""
        match = re.search(
            r"```(?:json)?\s*\n?(.*?)\n?\s*```",
            text,
            re.DOTALL,
        )
        if match:
            return match.group(1).strip()
        return text
