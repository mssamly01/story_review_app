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
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "markdown", "json", "csv", "review-txt", "prompts-txt"
        ])
        self.profile_combo = QComboBox()
        self.output_dir_label = QLabel("Chưa chọn thư mục xuất")
        self.btn_browse = QPushButton("Chọn thư mục...")
        
        form_layout.addWidget(QLabel("Tập truyện:"), 0, 0)
        form_layout.addWidget(self.ep_combo, 0, 1)
        form_layout.addWidget(QLabel("Định dạng:"), 1, 0)
        form_layout.addWidget(self.format_combo, 1, 1)
        form_layout.addWidget(QLabel("Profile:"), 2, 0)
        form_layout.addWidget(self.profile_combo, 2, 1)
        form_layout.addWidget(QLabel("Thư mục:"), 3, 0)
        form_layout.addWidget(self.output_dir_label, 3, 1)
        form_layout.addWidget(self.btn_browse, 3, 2)
        
        layout.addLayout(form_layout)
        
        btn_layout = QHBoxLayout()
        self.btn_export_format = QPushButton("Xuất theo định dạng")
        self.btn_export_profile = QPushButton("Xuất theo Profile")
        btn_layout.addWidget(self.btn_export_format)
        btn_layout.addWidget(self.btn_export_profile)
        layout.addLayout(btn_layout)
        
        layout.addWidget(QLabel("Các tệp đã tạo:"))
        self.created_files_list = QListWidget()
        layout.addWidget(self.created_files_list)
        
        # Connect signals
        self.btn_browse.clicked.connect(self._on_browse)
        self.btn_export_format.clicked.connect(self._on_export_format)
        self.btn_export_profile.clicked.connect(self._on_export_profile)

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

    def _on_export_format(self) -> None:
        """Export directly to a specific format."""
        if not self.app_state.project:
            return
        
        ep_id = self.ep_combo.currentData()
        output_dir = self.output_dir_label.text()
        fmt = self.format_combo.currentText()
        
        if not ep_id or "Chưa chọn" in output_dir:
            QMessageBox.warning(self, "Cảnh báo", "Hãy chọn tập và thư mục xuất.")
            return
            
        try:
            path = self.export_controller.export_episode(
                self.app_state.project, ep_id, fmt, output_dir
            )
            self.created_files_list.clear()
            self.created_files_list.addItem(str(path))
            QMessageBox.information(self, "Thông báo", f"Đã xuất: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_export_profile(self) -> None:
        """Export using a profile."""
        if not self.app_state.project:
            return
        
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
