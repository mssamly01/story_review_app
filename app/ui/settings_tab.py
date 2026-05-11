"""Tab for application settings and configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)

if TYPE_CHECKING:
    from app.ui.app_state import AppState

class SettingsTab(QWidget):
    def __init__(
        self,
        app_state: AppState,
        refresh_callback: callable,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.refresh_callback = refresh_callback
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 1. AI Configuration
        ai_group = QGroupBox("Cấu hình AI")
        ai_layout = QFormLayout(ai_group)

        self.ai_mode_combo = QComboBox()
        self.ai_mode_combo.addItems(["deterministic", "mock", "real"])
        self.ai_mode_combo.setCurrentText(self.app_state.ai_mode)
        ai_layout.addRow("Chế độ AI:", self.ai_mode_combo)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo", "claude-3-opus", "claude-3-sonnet"])
        self.model_combo.setEditable(True)
        self.model_combo.setCurrentText(self.app_state.model)
        ai_layout.addRow("Model:", self.model_combo)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Nhập API Key (nếu dùng chế độ real)")
        ai_layout.addRow("API Key:", self.api_key_input)

        layout.addWidget(ai_group)

        # 2. Manual AI Defaults
        manual_group = QGroupBox("Mặc định Manual AI")
        manual_layout = QFormLayout(manual_group)

        self.task_combo = QComboBox()
        self.task_combo.addItems([
            "generate-unified-package",
            "plan-episode",
            "generate-beats",
            "rewrite-review",
            "build-prompts",
        ])
        self.task_combo.setCurrentText(self.app_state.default_manual_ai_task)
        manual_layout.addRow("Task mặc định:", self.task_combo)

        layout.addWidget(manual_group)

        # 3. UI Preferences
        ui_group = QGroupBox("Giao diện & Hệ thống")
        ui_layout = QFormLayout(ui_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        self.theme_combo.setCurrentText(self.app_state.theme)
        ui_layout.addRow("Chủ đề:", self.theme_combo)

        layout.addWidget(ui_group)

        # Save Button
        self.btn_save = QPushButton("Lưu cài đặt")
        self.btn_save.setMinimumHeight(40)
        self.btn_save.setObjectName("primary-button")
        self.btn_save.clicked.connect(self._on_save)
        layout.addWidget(self.btn_save)

        layout.addStretch()

    def _on_save(self) -> None:
        self.app_state.ai_mode = self.ai_mode_combo.currentText()
        self.app_state.model = self.model_combo.currentText()
        self.app_state.default_manual_ai_task = self.task_combo.currentText()
        self.app_state.theme = self.theme_combo.currentText()
        
        # If real mode, we might want to set ENV var for the session
        if self.app_state.ai_mode == "real" and self.api_key_input.text():
            import os
            os.environ["OPENAI_API_KEY"] = self.api_key_input.text()

        QMessageBox.information(self, "Thành công", "Đã lưu cài đặt hệ thống.")
        self.refresh_callback()

    def refresh(self) -> None:
        self.ai_mode_combo.setCurrentText(self.app_state.ai_mode)
        self.model_combo.setCurrentText(self.app_state.model)
        self.task_combo.setCurrentText(self.app_state.default_manual_ai_task)
        self.theme_combo.setCurrentText(self.app_state.theme)
