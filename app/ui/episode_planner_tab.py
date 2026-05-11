"""Episode planner tab."""

from __future__ import annotations

from typing import TYPE_CHECKING
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)

if TYPE_CHECKING:
    from app.ui.app_state import AppState
    from app.controllers.project_controller import ProjectController
    from app.controllers.generation_controller import GenerationController
    from app.controllers.batch_workflow_controller import BatchWorkflowController

ITEM_ROLE = Qt.ItemDataRole.UserRole


class EpisodePlannerTab(QWidget):
    def __init__(
        self,
        app_state: AppState,
        project_controller: ProjectController,
        generation_controller: GenerationController,
        batch_controller: BatchWorkflowController,
        refresh_callback: callable,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.project_controller = project_controller
        self.generation_controller = generation_controller
        self.batch_controller = batch_controller
        self.refresh_callback = refresh_callback
        
        self._tone_map = {
            "bí ẩn": "mysterious",
            "kịch tính": "dramatic",
            "trung lập": "neutral",
            "hài hước": "humorous",
            "nhanh": "fast-paced",
        }
        self._density_map = {
            "đầy đủ": "full",
            "cân bằng": "balanced",
            "tóm gọn": "condensed",
        }

        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QHBoxLayout(self)

        # --- Left: Chapter Selector ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(QLabel("Chọn chương nguồn:"))
        self.chapter_list = QListWidget()
        self.chapter_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        left_layout.addWidget(self.chapter_list)
        main_layout.addWidget(left_widget, 1)

        # --- Middle: Planner Controls ---
        mid_widget = QWidget()
        mid_layout = QVBoxLayout(mid_widget)
        
        form_group = QGridLayout()
        self.title_edit = QLineEdit("Tập 1")
        self.tone_combo = QComboBox()
        self.tone_combo.addItems(list(self._tone_map.keys()))
        self.density_combo = QComboBox()
        self.density_combo.addItems(list(self._density_map.keys()))
        
        form_group.addWidget(QLabel("Tiêu đề tập:"), 0, 0)
        form_group.addWidget(self.title_edit, 0, 1)
        form_group.addWidget(QLabel("Phong cách (Tone):"), 1, 0)
        form_group.addWidget(self.tone_combo, 1, 1)
        form_group.addWidget(QLabel("Độ chi tiết:"), 2, 0)
        form_group.addWidget(self.density_combo, 2, 1)
        mid_layout.addLayout(form_group)

        self.btn_plan = QPushButton("Lập kế hoạch tập")
        self.btn_batch = QPushButton("Lập kế hoạch hàng loạt")
        mid_layout.addWidget(self.btn_plan)
        mid_layout.addWidget(self.btn_batch)
        mid_layout.addStretch()
        main_layout.addWidget(mid_widget, 1)

        # --- Right: Episode List ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.addWidget(QLabel("Danh sách tập truyện:"))
        self.episode_list = QListWidget()
        right_layout.addWidget(self.episode_list)
        main_layout.addWidget(right_widget, 1)

        # Connect signals
        self.btn_plan.clicked.connect(self._on_plan)
        self.btn_batch.clicked.connect(self._on_batch)
        self.episode_list.currentItemChanged.connect(self._on_episode_select)

    def refresh(self) -> None:
        self.chapter_list.clear()
        self.episode_list.clear()
        
        if not self.app_state.project:
            return

        for chapter in self.app_state.project.source_chapters:
            item = QListWidgetItem(f"{chapter.chapter_number} | {chapter.title}")
            item.setData(ITEM_ROLE, chapter.chapter_id)
            self.chapter_list.addItem(item)
            if chapter.chapter_id == self.app_state.selected_chapter_id:
                item.setSelected(True)

        for ep in self.app_state.project.review_episodes:
            item = QListWidgetItem(f"{ep.episode_id} | {ep.title}")
            item.setData(ITEM_ROLE, ep.episode_id)
            self.episode_list.addItem(item)
            if ep.episode_id == self.app_state.selected_episode_id:
                self.episode_list.setCurrentItem(item)

    def _on_episode_select(self, current: QListWidgetItem | None, previous: object) -> None:
        if current:
            self.app_state.selected_episode_id = current.data(ITEM_ROLE)
        else:
            self.app_state.selected_episode_id = None

    def _on_plan(self) -> None:
        selected_items = self.chapter_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Cảnh báo", "Hãy chọn ít nhất một chương.")
            return
            
        chapter_ids = [item.data(ITEM_ROLE) for item in selected_items]
        # We use the first one as primary for some logic, or pass list if service supports it
        # Current GenerationController.plan_episode takes one chapter_id.
        # I'll use the first one to match existing controller.
        
        try:
            episode = self.generation_controller.plan_episode(
                self.app_state.project,
                chapter_id=chapter_ids[0],
                episode_title=self.title_edit.text(),
                tone=self._tone_map[self.tone_combo.currentText()],
                density=self._density_map[self.density_combo.currentText()],
                ai_mode=self.app_state.ai_mode,
                model=self.app_state.model,
            )
            self.app_state.selected_episode_id = episode.episode_id
            self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_batch(self) -> None:
        if not self.app_state.project:
            return
        
        try:
            # Batch planner usually auto-plans for all chapters
            self.batch_controller.run_batch_onboarding(
                self.app_state.project,
                tone=self._tone_map[self.tone_combo.currentText()],
                density=self._density_map[self.density_combo.currentText()],
                ai_mode=self.app_state.ai_mode,
                model=self.app_state.model,
            )
            QMessageBox.information(self, "Thông báo", "Đã lập kế hoạch hàng loạt.")
            self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))
