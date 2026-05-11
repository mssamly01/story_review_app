"""Main PySide6 window with workflow-based multi-tab interface."""

from __future__ import annotations

from typing import Any
from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QStatusBar,
    QMessageBox,
)

from app.ui.app_state import AppState
from app.ui.project_tab import ProjectTab
from app.ui.source_tab import SourceTab
from app.ui.episode_planner_tab import EpisodePlannerTab
from app.ui.beat_studio_tab import BeatStudioTab
from app.ui.bible_style_tab import BibleStyleTab
from app.ui.quality_repair_tab import QualityRepairTab
from app.ui.export_tab import ExportTab
from app.ui.manual_ai_tab import ManualAITab

from app.controllers.project_controller import ProjectController
from app.controllers.generation_controller import GenerationController
from app.controllers.export_controller import ExportController
from app.controllers.export_profile_controller import ExportProfileController
from app.controllers.bible_controller import BibleController
from app.controllers.validation_controller import ValidationController
from app.controllers.repair_controller import RepairController
from app.controllers.batch_workflow_controller import BatchWorkflowController
from app.controllers.production_readiness_controller import ProductionReadinessController
from app.controllers.prompt_quality_controller import PromptQualityController


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Story Review Studio")
        self.resize(1280, 800)

        # 1. Initialize State
        self.app_state = AppState()

        # 2. Initialize Controllers
        self.project_controller = ProjectController()
        ps = self.project_controller.project_service
        self.generation_controller = GenerationController(ps)
        self.export_controller = ExportController(ps)
        self.export_profile_controller = ExportProfileController(ps)
        self.bible_controller = BibleController(ps)
        self.validation_controller = ValidationController(ps)
        self.repair_controller = RepairController(ps)
        self.batch_controller = BatchWorkflowController(ps)
        self.readiness_controller = ProductionReadinessController(ps)
        self.quality_controller = PromptQualityController(ps)

        # 3. Build UI
        self._build_ui()
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.set_status("Sẵn sàng")

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.tabs = QTabWidget()
        
        # Create Tabs
        self.project_tab = ProjectTab(
            self.app_state, self.project_controller, self.refresh_all_tabs
        )
        self.source_tab = SourceTab(
            self.app_state, self.project_controller, self.generation_controller, self.refresh_all_tabs
        )
        self.planner_tab = EpisodePlannerTab(
            self.app_state, self.project_controller, self.generation_controller, 
            self.batch_controller, self.refresh_all_tabs
        )
        self.studio_tab = BeatStudioTab(
            self.app_state, self.generation_controller, self.refresh_all_tabs
        )
        self.bible_tab = BibleStyleTab(
            self.app_state, self.bible_controller, self.refresh_all_tabs
        )
        self.quality_tab = QualityRepairTab(
            self.app_state, 
            self.validation_controller, 
            self.repair_controller, 
            self.readiness_controller,
            self.quality_controller,
            self.refresh_all_tabs
        )
        self.export_tab = ExportTab(
            self.app_state, self.export_controller, self.export_profile_controller, self.refresh_all_tabs
        )
        self.manual_ai_tab = ManualAITab(
            self.app_state, self.project_controller, self.refresh_all_tabs
        )

        # Add to TabWidget
        self.tabs.addTab(self.project_tab, "Dự án")
        self.tabs.addTab(self.source_tab, "Nguồn")
        self.tabs.addTab(self.planner_tab, "Kế hoạch tập")
        self.tabs.addTab(self.studio_tab, "Beat Studio")
        self.tabs.addTab(self.bible_tab, "Bible / Style")
        self.tabs.addTab(self.quality_tab, "Chất lượng")
        self.tabs.addTab(self.export_tab, "Xuất bản")
        self.tabs.addTab(self.manual_ai_tab, "AI Thủ Công")

        layout.addWidget(self.tabs)
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index: int) -> None:
        """Auto-save project when switching tabs."""
        if self.app_state.project and self.project_controller.project_path:
            try:
                self.project_controller.save_project()
            except Exception:
                pass # Don't block UI on auto-save failure
        
        tab = self.tabs.widget(index)
        if hasattr(tab, "refresh"):
            tab.refresh()

    def refresh_all_tabs(self) -> None:
        """Sync AppState with controllers and refresh every tab."""
        self.app_state.project = self.project_controller.project
        self.app_state.project_path = self.project_controller.project_path
        
        self.project_tab.refresh()
        self.source_tab.refresh()
        self.planner_tab.refresh()
        self.studio_tab.refresh()
        self.bible_tab.refresh()
        self.quality_tab.refresh()
        self.export_tab.refresh()
        self.manual_ai_tab.refresh()
        
        self.set_status("Đã cập nhật")

    def set_status(self, message: str) -> None:
        self.statusBar.showMessage(message)

    def show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Lỗi", message)


def create_main_window() -> tuple[Any, MainWindow]:
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    return app, window
