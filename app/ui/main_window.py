"""Main PySide6 window with workflow-based multi-tab interface.

Layout (post-redesign):

* **Header toolbar** — app title, project path, AI-mode chip, theme toggle.
* **Vertical sidebar** — 7 workflow steps (replaces the original top tab bar).
  Implemented via :class:`SidebarTabWidget`, which keeps the ``QTabWidget``
  API so existing UI tests don't have to change.
* **Status bar** — current message + theme indicator.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.controllers.batch_workflow_controller import BatchWorkflowController
from app.controllers.bible_controller import BibleController
from app.controllers.export_controller import ExportController
from app.controllers.export_profile_controller import ExportProfileController
from app.controllers.generation_controller import GenerationController
from app.controllers.manual_ai_controller import ManualAIController
from app.controllers.production_readiness_controller import ProductionReadinessController
from app.controllers.project_controller import ProjectController
from app.controllers.prompt_quality_controller import PromptQualityController
from app.controllers.repair_controller import RepairController
from app.controllers.validation_controller import ValidationController
from app.ui.app_state import AppState
from app.ui.beat_studio_tab import BeatStudioTab
from app.ui.bible_style_tab import BibleStyleTab
from app.ui.episode_planner_tab import EpisodePlannerTab
from app.ui.export_tab import ExportTab
from app.ui.project_tab import ProjectTab
from app.ui.quality_repair_tab import QualityRepairTab
from app.ui.sidebar_tabs import SidebarTabWidget
from app.ui.source_tab import SourceTab
from app.ui.theme import (
    Theme,
    apply_theme,
    current_theme,
    load_persisted_theme,
    save_persisted_theme,
)


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Story Review Studio")
        self.resize(1360, 860)

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
        self.manual_ai_controller = ManualAIController(ps)

        # 3. Build UI
        self._build_menu()
        self._build_header()
        self._build_ui()
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self._theme_label = QLabel(f"Theme: {current_theme().value}")
        self.statusBar.addPermanentWidget(self._theme_label)
        self.set_status("Sẵn sàng")
        self._update_header()

    # ------------------------------------------------------------------
    # UI building
    # ------------------------------------------------------------------
    def _build_menu(self) -> None:
        menubar = self.menuBar()
        view_menu = menubar.addMenu("&View")

        theme_menu = view_menu.addMenu("Theme")
        self._theme_action_group = QActionGroup(self)
        self._theme_action_group.setExclusive(True)

        active = current_theme()
        for theme in (Theme.DARK, Theme.LIGHT):
            action = QAction(theme.value.capitalize(), self, checkable=True)
            action.setData(theme)
            action.setChecked(theme == active)
            action.triggered.connect(lambda _checked, t=theme: self._on_theme_selected(t))
            theme_menu.addAction(action)
            self._theme_action_group.addAction(action)

    def _build_header(self) -> None:
        header = QToolBar("App header", self)
        header.setObjectName("app-header")
        header.setMovable(False)
        header.setFloatable(False)
        header.setAllowedAreas(Qt.ToolBarArea.TopToolBarArea)

        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(10)

        self._app_title_label = QLabel("Story Review Studio")
        self._app_title_label.setObjectName("app-title")
        title_layout.addWidget(self._app_title_label)

        self._project_label = QLabel("Chưa mở dự án nào")
        self._project_label.setObjectName("project-path")
        title_layout.addWidget(self._project_label, 1)

        header.addWidget(title_widget)

        spacer = QWidget()
        spacer.setSizePolicy(
            spacer.sizePolicy().horizontalPolicy(), spacer.sizePolicy().verticalPolicy()
        )
        header.addWidget(spacer)

        self._ai_chip = QLabel("AI: deterministic")
        self._ai_chip.setObjectName("status-chip")
        header.addWidget(self._ai_chip)

        self._theme_button = QToolButton(self)
        self._theme_button.setObjectName("header-button")
        self._theme_button.setText(self._theme_button_text())
        self._theme_button.clicked.connect(self._toggle_theme)
        header.addWidget(self._theme_button)

        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, header)
        self._header = header

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("tab-page")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = SidebarTabWidget()

        # Create Tabs
        self.project_tab = ProjectTab(
            self.app_state, self.project_controller, self.refresh_all_tabs
        )
        self.source_tab = SourceTab(
            self.app_state,
            self.project_controller,
            self.generation_controller,
            self.manual_ai_controller,
            self.refresh_all_tabs,
        )
        self.planner_tab = EpisodePlannerTab(
            self.app_state,
            self.project_controller,
            self.generation_controller,
            self.batch_controller,
            self.manual_ai_controller,
            self.refresh_all_tabs,
        )
        self.studio_tab = BeatStudioTab(
            self.app_state,
            self.generation_controller,
            self.manual_ai_controller,
            self.refresh_all_tabs,
        )
        self.bible_tab = BibleStyleTab(self.app_state, self.bible_controller, self.refresh_all_tabs)
        self.quality_tab = QualityRepairTab(
            self.app_state,
            self.validation_controller,
            self.repair_controller,
            self.readiness_controller,
            self.quality_controller,
            self.refresh_all_tabs,
        )
        self.export_tab = ExportTab(
            self.app_state,
            self.export_controller,
            self.export_profile_controller,
            self.refresh_all_tabs,
        )

        # Wrap each tab so it gets a consistent inner margin without each tab
        # having to repeat that layout.
        def _wrap(tab_widget: QWidget) -> QWidget:
            wrapper = QFrame()
            wrapper.setObjectName("tab-page")
            wlayout = QVBoxLayout(wrapper)
            wlayout.setContentsMargins(16, 16, 16, 16)
            wlayout.addWidget(tab_widget)
            return wrapper

        # Add to sidebar nav (signature compatible with QTabWidget.addTab).
        # Track the ordered list of inner tabs so _on_tab_changed can call
        # ``refresh()`` without having to dig through the wrapper widget tree.
        self._ordered_tabs: list[QWidget] = [
            self.project_tab,
            self.source_tab,
            self.bible_tab,
            self.planner_tab,
            self.studio_tab,
            self.quality_tab,
            self.export_tab,
        ]
        self.tabs.addTab(_wrap(self.project_tab), "Dự án")
        self.tabs.addTab(_wrap(self.source_tab), "Nguồn")
        self.tabs.addTab(_wrap(self.bible_tab), "Bible / Style")
        self.tabs.addTab(_wrap(self.planner_tab), "Kế hoạch tập")
        self.tabs.addTab(_wrap(self.studio_tab), "Beat Studio")
        self.tabs.addTab(_wrap(self.quality_tab), "Chất lượng")
        self.tabs.addTab(_wrap(self.export_tab), "Xuất bản")

        layout.addWidget(self.tabs)
        self.tabs.currentChanged.connect(self._on_tab_changed)

    # ------------------------------------------------------------------
    # Tab change / refresh
    # ------------------------------------------------------------------
    def _on_tab_changed(self, index: int) -> None:
        """Auto-save project when switching tabs."""
        if self.app_state.project and self.project_controller.project_path:
            try:
                self.project_controller.save_project()
            except Exception:
                pass  # Don't block UI on auto-save failure

        if 0 <= index < len(self._ordered_tabs):
            tab = self._ordered_tabs[index]
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

        self._update_header()
        self.set_status("Đã cập nhật")

    def set_status(self, message: str) -> None:
        self.statusBar.showMessage(message)

    def show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Lỗi", message)

    # ------------------------------------------------------------------
    # Header / theme bookkeeping
    # ------------------------------------------------------------------
    def _update_header(self) -> None:
        if self.app_state.project:
            self._project_label.setText(
                f"{self.app_state.project.title}"
                + (f"  ·  {self.app_state.project_path}" if self.app_state.project_path else "")
            )
        else:
            self._project_label.setText("Chưa mở dự án nào")

        self._ai_chip.setText(f"AI: {self.app_state.ai_mode}")

    def _theme_button_text(self) -> str:
        return "Light theme" if current_theme() == Theme.DARK else "Dark theme"

    def _on_theme_selected(self, theme: Theme) -> None:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return
        apply_theme(app, theme)
        save_persisted_theme(theme)
        self._theme_button.setText(self._theme_button_text())
        self._theme_label.setText(f"Theme: {theme.value}")
        for action in self._theme_action_group.actions():
            action.setChecked(action.data() == theme)

    def _toggle_theme(self) -> None:
        current = current_theme()
        target = Theme.LIGHT if current == Theme.DARK else Theme.DARK
        self._on_theme_selected(target)


def create_main_window() -> tuple[Any, MainWindow]:
    import sys

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    apply_theme(app, load_persisted_theme())
    window = MainWindow()
    return app, window
