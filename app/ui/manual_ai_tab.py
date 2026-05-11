"""Tab for manual AI workflow: export prompt → external AI → import result."""

from __future__ import annotations

from typing import TYPE_CHECKING
from PySide6.QtWidgets import (
    QComboBox, QGridLayout, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
    QDialog,
)

if TYPE_CHECKING:
    from app.ui.app_state import AppState
    from app.controllers.project_controller import ProjectController

from app.services.manual_ai_service import ManualAIService, SUPPORTED_STEPS
from app.ui.manual_ai_dialogs import PromptExportDialog, ResultImportDialog

_STEP_LABELS = {
    "parse-story": "Phân tích truyện",
    "plan-episode": "Lập kế hoạch tập",
    "generate-beats": "Tạo nhịp truyện",
    "rewrite-review": "Viết lại Review",
    "build-prompts": "Xây dựng Prompt ảnh",
}


class ManualAITab(QWidget):
    def __init__(
        self,
        app_state: AppState,
        project_controller: ProjectController,
        refresh_callback: callable,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.project_controller = project_controller
        self.refresh_callback = refresh_callback
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Step selector
        form = QGridLayout()
        self.step_combo = QComboBox()
        for step in SUPPORTED_STEPS:
            self.step_combo.addItem(_STEP_LABELS.get(step, step), step)
        form.addWidget(QLabel("Bước pipeline:"), 0, 0)
        form.addWidget(self.step_combo, 0, 1)
        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_export = QPushButton("Lấy Prompt (Popup)")
        self.btn_import = QPushButton("Dán kết quả (Popup)")
        btn_layout.addWidget(self.btn_export)
        btn_layout.addWidget(self.btn_import)
        layout.addLayout(btn_layout)
        
        layout.addStretch()

        # Connect
        self.btn_export.clicked.connect(self._on_export)
        self.btn_import.clicked.connect(self._on_import)

    def refresh(self) -> None:
        pass

    def _get_service(self) -> ManualAIService:
        return ManualAIService(self.project_controller.project_service)

    def _on_export(self) -> None:
        if not self.app_state.project:
            QMessageBox.warning(self, "Cảnh báo", "Hãy mở dự án trước.")
            return

        step = self.step_combo.currentData()
        step_label = self.step_combo.currentText()
        try:
            service = self._get_service()
            exported = service.export_prompt(
                self.app_state.project,
                step=step,
                chapter_id=self.app_state.selected_chapter_id,
                episode_id=self.app_state.selected_episode_id,
            )
            prompt_text = service.format_prompt_for_clipboard(exported)
            
            dialog = PromptExportDialog(prompt_text, step_label, self)
            dialog.exec()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_import(self) -> None:
        if not self.app_state.project:
            QMessageBox.warning(self, "Cảnh báo", "Hãy mở dự án trước.")
            return

        step = self.step_combo.currentData()
        step_label = self.step_combo.currentText()
        
        dialog = ResultImportDialog(step_label, self)
        if dialog.exec() == QDialog.Accepted:
            result_data = dialog.get_result_data()
            if result_data is None:
                return
            try:
                service = self._get_service()
                message = service.import_result(
                    self.app_state.project,
                    step=step,
                    result_data=result_data,
                    chapter_id=self.app_state.selected_chapter_id,
                    episode_id=self.app_state.selected_episode_id,
                )
                QMessageBox.information(self, "Thông báo", message)
                self.refresh_callback()
            except Exception as exc:
                QMessageBox.critical(self, "Lỗi", str(exc))
