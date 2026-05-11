"""Tab for exporting episodes."""

from __future__ import annotations

from typing import TYPE_CHECKING
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)

if TYPE_CHECKING:
    from app.ui.app_state import AppState
    from app.controllers.export_controller import ExportController
    from app.controllers.export_profile_controller import ExportProfileController


class ExportTab(QWidget):
    def __init__(
        self,
        app_state: AppState,
        export_controller: ExportController,
        profile_controller: ExportProfileController,
        refresh_callback: callable,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.export_controller = export_controller
        self.profile_controller = profile_controller
        self.refresh_callback = refresh_callback
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        form_layout = QGridLayout()
        self.ep_combo = QComboBox()
        self.profile_combo = QComboBox()
        self.output_dir_label = QLabel("Chưa chọn thư mục xuất")
        self.btn_browse = QPushButton("Chọn thư mục...")
        
        form_layout.addWidget(QLabel("Tập truyện:"), 0, 0)
        form_layout.addWidget(self.ep_combo, 0, 1)
        form_layout.addWidget(QLabel("Profile:"), 1, 0)
        form_layout.addWidget(self.profile_combo, 1, 1)
        form_layout.addWidget(QLabel("Thư mục:"), 2, 0)
        form_layout.addWidget(self.output_dir_label, 2, 1)
        form_layout.addWidget(self.btn_browse, 2, 2)
        
        layout.addLayout(form_layout)
        
        self.btn_export = QPushButton("Thực hiện Xuất bản")
        layout.addWidget(self.btn_export)
        
        layout.addWidget(QLabel("Các tệp đã tạo:"))
        self.created_files_list = QListWidget()
        layout.addWidget(self.created_files_list)
        
        # Connect signals
        self.btn_browse.clicked.connect(self._on_browse)
        self.btn_export.clicked.connect(self._on_export)

    def refresh(self) -> None:
        self.ep_combo.clear()
        self.profile_combo.clear()
        
        if not self.app_state.project:
            return
            
        for ep in self.app_state.project.review_episodes:
            self.ep_combo.addItem(ep.title, ep.episode_id)
            
        try:
            profiles = self.profile_controller.list_profiles()
            for p in profiles:
                self.profile_combo.addItem(p.name, p.profile_id)
        except:
            pass

    def _on_browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Chọn thư mục xuất")
        if path:
            self.output_dir_label.setText(path)

    def _on_export(self) -> None:
        if not self.app_state.project: return
        
        ep_id = self.ep_combo.currentData()
        profile_id = self.profile_combo.currentData()
        output_dir = self.output_dir_label.text()
        
        if not ep_id or not profile_id or "Chưa chọn" in output_dir:
            QMessageBox.warning(self, "Cảnh báo", "Hãy chọn tập, profile và thư mục xuất.")
            return
            
        try:
            paths = self.profile_controller.export_episode_with_profile(
                self.app_state.project, ep_id, profile_id, output_dir
            )
            self.created_files_list.clear()
            for p in paths:
                self.created_files_list.addItem(str(p))
            QMessageBox.information(self, "Thông báo", "Xuất bản hoàn tất.")
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))
