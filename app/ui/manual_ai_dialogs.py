"""Dialog windows for manual AI workflow: export prompt & import result."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class PromptExportDialog(QDialog):
    """Cửa sổ hiển thị prompt — user copy để paste vào AI bên ngoài."""

    def __init__(self, prompt_text: str, step_label: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Lấy Prompt — {step_label}")
        self.setMinimumSize(800, 600)
        self.prompt_text = prompt_text
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Copy toàn bộ nội dung bên dưới → paste vào ChatGPT / Claude / Gemini.\n"
            "AI sẽ trả về JSON → dùng nút 'Dán kết quả' để import lại vào app."
        ))

        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self.prompt_text)
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

        btn_layout = QHBoxLayout()
        btn_copy = QPushButton("Copy vào Clipboard")
        btn_copy.clicked.connect(self._on_copy)
        btn_layout.addWidget(btn_copy)

        btn_close = QPushButton("Đóng")
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    def _on_copy(self) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(self.prompt_text)
        QMessageBox.information(self, "Thông báo", "Đã copy vào clipboard!")


class ResultImportDialog(QDialog):
    """Cửa sổ để user paste JSON result từ AI bên ngoài."""

    def __init__(self, step_label: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Dán kết quả — {step_label}")
        self.setMinimumSize(800, 600)
        self.result_json: str | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Paste JSON result từ ChatGPT / Claude vào ô bên dưới.\n"
            "Chỉ paste phần JSON (bắt đầu bằng { hoặc [).\n"
            "App sẽ tự động bỏ markdown code block nếu có."
        ))

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(
            '{\n'
            '  "scenes": [\n'
            '    {\n'
            '      "scene_id": "sc_001",\n'
            '      "title": "...",\n'
            '      "summary": "..."\n'
            '    }\n'
            '  ]\n'
            '}'
        )
        layout.addWidget(self.text_edit)

        btn_layout = QHBoxLayout()
        btn_paste = QPushButton("Paste từ Clipboard")
        btn_paste.clicked.connect(self._on_paste)
        btn_layout.addWidget(btn_paste)

        btn_apply = QPushButton("Áp dụng kết quả")
        btn_apply.clicked.connect(self._on_apply)
        btn_layout.addWidget(btn_apply)

        btn_cancel = QPushButton("Hủy")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def _on_paste(self) -> None:
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.text_edit.setPlainText(text)

    def _on_apply(self) -> None:
        import json
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Cảnh báo", "Chưa có nội dung JSON.")
            return

        if text.startswith("```"):
            lines = text.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            json.loads(text)
            self.result_json = text
            self.accept()
        except json.JSONDecodeError as exc:
            QMessageBox.critical(
                self, "Lỗi JSON",
                f"JSON không hợp lệ:\n{exc}\n\n"
                "Hãy kiểm tra lại kết quả từ AI — chỉ paste phần JSON.",
            )

    def get_result_data(self) -> dict | None:
        import json
        if self.result_json:
            return json.loads(self.result_json)
        return None
