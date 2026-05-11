"""Tab for validation, continuity check, and repairs."""

from __future__ import annotations

from typing import TYPE_CHECKING
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QPlainTextEdit,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)

if TYPE_CHECKING:
    from app.ui.app_state import AppState
    from app.controllers.validation_controller import ValidationController
    from app.controllers.repair_controller import RepairController


class QualityRepairTab(QWidget):
    def __init__(
        self,
        app_state: AppState,
        validation_controller: ValidationController,
        repair_controller: RepairController,
        refresh_callback: callable,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.validation_controller = validation_controller
        self.repair_controller = repair_controller
        self.refresh_callback = refresh_callback
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Chọn tập truyện:"))
        self.ep_combo = QComboBox()
        top_layout.addWidget(self.ep_combo, 1)
        layout.addLayout(top_layout)

        content_layout = QHBoxLayout()
        
        # Action column
        btn_layout = QVBoxLayout()
        self.btn_validate = QPushButton("Kiểm tra dự án")
        self.btn_continuity = QPushButton("Kiểm tra tính nhất quán")
        self.btn_readiness = QPushButton("Báo cáo sẵn sàng")
        self.btn_suggest = QPushButton("Gợi ý sửa lỗi")
        self.btn_repair = QPushButton("Áp dụng sửa lỗi (Rủi ro thấp)")
        
        btn_layout.addWidget(self.btn_validate)
        btn_layout.addWidget(self.btn_continuity)
        btn_layout.addWidget(self.btn_readiness)
        btn_layout.addWidget(self.btn_suggest)
        btn_layout.addWidget(self.btn_repair)
        btn_layout.addStretch()
        content_layout.addLayout(btn_layout)

        # Results area
        self.results_table = QTableWidget(0, 3)
        self.results_table.setHorizontalHeaderLabels(["Loại", "Mức độ", "Thông điệp"])
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        content_layout.addWidget(self.results_table, 1)
        
        layout.addLayout(content_layout)

    def refresh(self) -> None:
        self.ep_combo.clear()
        if not self.app_state.project:
            return
            
        for ep in self.app_state.project.review_episodes:
            self.ep_combo.addItem(ep.title, ep.episode_id)
