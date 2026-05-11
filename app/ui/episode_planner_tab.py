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
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from app.controllers.batch_workflow_controller import BatchWorkflowController
    from app.controllers.generation_controller import GenerationController
    from app.controllers.manual_ai_controller import ManualAIController
    from app.controllers.project_controller import ProjectController
    from app.ui.app_state import AppState

from app.ui.manual_ai_dialogs import PromptExportDialog, ResultImportDialog

ITEM_ROLE = Qt.ItemDataRole.UserRole


class EpisodePlannerTab(QWidget):
    def __init__(
        self,
        app_state: AppState,
        project_controller: ProjectController,
        generation_controller: GenerationController,
        batch_controller: BatchWorkflowController,
        manual_ai_controller: ManualAIController,
        refresh_callback: callable,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.project_controller = project_controller
        self.generation_controller = generation_controller
        self.batch_controller = batch_controller
        self.manual_ai_controller = manual_ai_controller
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

        mid_layout.addWidget(QLabel("── Manual AI ──"))
        self.btn_prompt_plan = QPushButton("Lấy Prompt Plan Episode")
        self.btn_import_plan = QPushButton("Dán kết quả Plan")
        mid_layout.addWidget(self.btn_prompt_plan)
        mid_layout.addWidget(self.btn_import_plan)

        mid_layout.addStretch()
        main_layout.addWidget(mid_widget, 1)

        # --- Right: Episode List ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.addWidget(QLabel("Danh sách tập truyện:"))
        self.episode_list = QListWidget()
        right_layout.addWidget(self.episode_list)
        self.btn_delete_episode = QPushButton("Xóa tập")
        right_layout.addWidget(self.btn_delete_episode)
        main_layout.addWidget(right_widget, 1)

        # Connect signals
        self.btn_delete_episode.clicked.connect(self._on_delete_episode)
        self.btn_prompt_plan.clicked.connect(self._on_prompt_plan)
        self.btn_import_plan.clicked.connect(self._on_import_plan)
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

    def _on_delete_episode(self) -> None:
        """Xóa tập truyện đang chọn khỏi project."""
        if not self.app_state.project or not self.app_state.selected_episode_id:
            QMessageBox.warning(self, "Cảnh báo", "Hãy chọn tập cần xóa.")
            return

        episode_id = self.app_state.selected_episode_id
        episode_name = episode_id
        for ep in self.app_state.project.review_episodes:
            if ep.episode_id == episode_id:
                episode_name = ep.title
                break

        reply = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa tập '{episode_name}'?\nTất cả scenes và beats trong tập này sẽ bị xóa.\nHành động này không thể hoàn tác.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.app_state.project.review_episodes = [
            ep for ep in self.app_state.project.review_episodes if ep.episode_id != episode_id
        ]
        self.app_state.project.touch()
        self.app_state.selected_episode_id = None
        self.app_state.selected_scene_id = None
        self.app_state.selected_beat_id = None
        self.refresh_callback()

    def _selected_chapter_id(self) -> str | None:
        selected_items = self.chapter_list.selectedItems()
        if not selected_items:
            return None
        return selected_items[0].data(ITEM_ROLE)

    def _current_tone(self) -> str:
        return self._tone_map.get(self.tone_combo.currentText(), "mysterious")

    def _current_density(self) -> str:
        return self._density_map.get(self.density_combo.currentText(), "full")

    def _on_prompt_plan(self) -> None:
        if not self.app_state.project:
            QMessageBox.warning(self, "Cảnh báo", "Hãy tạo hoặc mở dự án trước.")
            return
        chapter_id = self._selected_chapter_id()
        if not chapter_id:
            QMessageBox.warning(self, "Cảnh báo", "Hãy chọn ít nhất một chương.")
            return
        try:
            prompt_text = self.manual_ai_controller.export_prompt(
                self.app_state.project,
                "plan-episode",
                chapter_id=chapter_id,
                tone=self._current_tone(),
                density=self._current_density(),
            )
            dialog = PromptExportDialog(prompt_text, "Plan Episode", self)
            dialog.exec()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_import_plan(self) -> None:
        if not self.app_state.project:
            QMessageBox.warning(self, "Cảnh báo", "Hãy tạo hoặc mở dự án trước.")
            return
        chapter_id = self._selected_chapter_id()
        if not chapter_id:
            QMessageBox.warning(self, "Cảnh báo", "Hãy chọn ít nhất một chương.")
            return
        try:
            dialog = ResultImportDialog("Plan Episode", self)
            if dialog.exec() and dialog.result_data is not None:
                summary = self.manual_ai_controller.import_result(
                    self.app_state.project,
                    "plan-episode",
                    dialog.result_data,
                    chapter_id=chapter_id,
                    tone=self._current_tone(),
                    density=self._current_density(),
                )
                QMessageBox.information(self, "Thành công", summary)
                self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))
