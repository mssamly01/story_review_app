"""Tab for validation, continuity check, and repairs."""

from __future__ import annotations

from typing import TYPE_CHECKING
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
)

if TYPE_CHECKING:
    from app.ui.app_state import AppState
    from app.controllers.validation_controller import ValidationController
    from app.controllers.repair_controller import RepairController
    from app.controllers.production_readiness_controller import ProductionReadinessController
    from app.controllers.prompt_quality_controller import PromptQualityController


class QualityRepairTab(QWidget):
    def __init__(
        self,
        app_state: AppState,
        validation_controller: ValidationController,
        repair_controller: RepairController,
        readiness_controller: ProductionReadinessController,
        quality_controller: PromptQualityController,
        refresh_callback: callable,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.validation_controller = validation_controller
        self.repair_controller = repair_controller
        self.readiness_controller = readiness_controller
        self.quality_controller = quality_controller
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

        # Connect signals
        self.btn_validate.clicked.connect(self._on_validate)
        self.btn_continuity.clicked.connect(self._on_continuity)
        self.btn_readiness.clicked.connect(self._on_readiness)
        self.btn_suggest.clicked.connect(self._on_suggest)
        self.btn_repair.clicked.connect(self._on_repair)

    def refresh(self) -> None:
        self.ep_combo.clear()
        if not self.app_state.project:
            return
            
        for ep in self.app_state.project.review_episodes:
            self.ep_combo.addItem(ep.title, ep.episode_id)

    def _on_validate(self) -> None:
        if not self.app_state.project:
            return
        try:
            issues = self.validation_controller.validate_project(self.app_state.project)
            self._show_issues(issues)
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_continuity(self) -> None:
        if not self.app_state.project:
            return
        ep_id = self.ep_combo.currentData()
        if not ep_id:
            return
        try:
            # In current controller, validate_project with ep_id checks continuity
            issues = self.validation_controller.validate_project(self.app_state.project, ep_id)
            self._show_issues(issues)
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_readiness(self) -> None:
        if not self.app_state.project:
            return
        ep_id = self.ep_combo.currentData()
        if not ep_id:
            return
        try:
            report = self.readiness_controller.build_episode_report(self.app_state.project, ep_id)
            self.results_table.setRowCount(1)
            self.results_table.setItem(0, 0, QTableWidgetItem("Readiness"))
            self.results_table.setItem(0, 1, QTableWidgetItem(
                "Sẵn sàng" if report.get("is_ready") else "Chưa sẵn sàng"
            ))
            self.results_table.setItem(0, 2, QTableWidgetItem(f"Điểm: {report.get('score', 0)}"))
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_suggest(self) -> None:
        if not self.app_state.project:
            return
        try:
            suggestions = self.repair_controller.suggest_repairs_for_project(self.app_state.project)
            self._show_suggestions(suggestions)
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_repair(self) -> None:
        if not self.app_state.project:
            return
        try:
            applied = self.repair_controller.apply_low_risk_repairs(self.app_state.project)
            self.results_table.setRowCount(1)
            self.results_table.setItem(0, 0, QTableWidgetItem("Repair"))
            self.results_table.setItem(0, 1, QTableWidgetItem("OK"))
            self.results_table.setItem(0, 2, QTableWidgetItem(
                f"Đã áp dụng {len(applied)} sửa lỗi rủi ro thấp."
            ))
            self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _show_issues(self, issues) -> None:
        self.results_table.setRowCount(len(issues))
        for row, issue in enumerate(issues):
            self.results_table.setItem(row, 0, QTableWidgetItem(getattr(issue, "category", "unknown")))
            self.results_table.setItem(row, 1, QTableWidgetItem(getattr(issue, "severity", "info")))
            self.results_table.setItem(row, 2, QTableWidgetItem(getattr(issue, "message", str(issue))))

    def _show_suggestions(self, suggestions) -> None:
        self.results_table.setRowCount(len(suggestions))
        for row, s in enumerate(suggestions):
            self.results_table.setItem(row, 0, QTableWidgetItem(getattr(s, "category", "repair")))
            self.results_table.setItem(row, 1, QTableWidgetItem(getattr(s, "risk_level", "unknown")))
            self.results_table.setItem(row, 2, QTableWidgetItem(getattr(s, "description", str(s))))
