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
    QFileDialog,
    QDialog,
)

if TYPE_CHECKING:
    from app.ui.app_state import AppState
    from app.controllers.project_controller import ProjectController
    from app.controllers.generation_controller import GenerationController
    from app.controllers.batch_workflow_controller import BatchWorkflowController

from app.services.manual_ai_service import ManualAIService
from app.ui.manual_ai_dialogs import PromptExportDialog, ResultImportDialog

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
        self.btn_pipeline = QPushButton("Chạy Full Pipeline cho tập đã chọn")
        mid_layout.addWidget(self.btn_plan)
        mid_layout.addWidget(self.btn_batch)
        mid_layout.addWidget(self.btn_pipeline)

        # Manual AI Section
        manual_layout = QHBoxLayout()
        self.btn_export_plan = QPushButton("Lấy Prompt Plan")
        self.btn_import_plan = QPushButton("Dán kết quả Plan")
        manual_layout.addWidget(self.btn_export_plan)
        manual_layout.addWidget(self.btn_import_plan)
        mid_layout.addLayout(manual_layout)

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
        self.btn_plan.clicked.connect(self._on_plan)
        self.btn_batch.clicked.connect(self._on_batch)
        self.btn_pipeline.clicked.connect(self._on_full_pipeline)
        self.btn_delete_episode.clicked.connect(self._on_delete_episode)
        self.btn_export_plan.clicked.connect(self._on_export_plan)
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
            self, "Xác nhận xóa",
            f"Bạn có chắc muốn xóa tập '{episode_name}'?\nTất cả scenes và beats trong tập này sẽ bị xóa.\nHành động này không thể hoàn tác.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.app_state.project.review_episodes = [
            ep for ep in self.app_state.project.review_episodes
            if ep.episode_id != episode_id
        ]
        self.app_state.project.touch()
        self.app_state.selected_episode_id = None
        self.app_state.selected_scene_id = None
        self.app_state.selected_beat_id = None
        self.refresh_callback()

    def _on_plan(self) -> None:
        selected_items = self.chapter_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Cảnh báo", "Hãy chọn ít nhất một chương.")
            return
            
        chapter_ids = [item.data(ITEM_ROLE) for item in selected_items]
        
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
        
        selected_items = self.chapter_list.selectedItems()
        chapter_ids = [item.data(ITEM_ROLE) for item in selected_items]

        if not chapter_ids:
            # If no chapters selected, use all available chapters
            chapter_ids = [ch.chapter_id for ch in self.app_state.project.source_chapters]

        if not chapter_ids:
            QMessageBox.warning(self, "Cảnh báo", "Không có chương nào để lập kế hoạch.")
            return

        try:
            self.batch_controller.plan_episodes_from_chapters(
                self.app_state.project,
                chapter_ids=chapter_ids,
                tone=self._tone_map[self.tone_combo.currentText()],
                density=self._density_map[self.density_combo.currentText()],
                ai_mode=self.app_state.ai_mode,
                model=self.app_state.model,
            )
            QMessageBox.information(self, "Thông báo", "Đã lập kế hoạch hàng loạt.")
            self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_full_pipeline(self) -> None:
        ep_id = self.app_state.selected_episode_id
        if not ep_id or not self.app_state.project:
            QMessageBox.warning(self, "Cảnh báo", "Hãy chọn một tập truyện.")
            return

        try:
            ep = self.generation_controller.find_episode(self.app_state.project, ep_id)
            
            # 1. Generate Beats
            self.generation_controller.generate_beats(
                self.app_state.project, ep_id,
                ai_mode=self.app_state.ai_mode,
                model=self.app_state.model,
            )
            # 2. Rewrite Review
            self.generation_controller.rewrite_review(
                self.app_state.project, ep_id,
                ai_mode=self.app_state.ai_mode,
                model=self.app_state.model,
            )
            # 3. Build Prompts
            self.generation_controller.build_prompts(
                self.app_state.project, ep_id,
                ai_mode=self.app_state.ai_mode,
                model=self.app_state.model,
            )
            
            QMessageBox.information(self, "Thông báo", f"Full pipeline hoàn tất cho tập '{ep.title}'.")
            self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_export_plan(self) -> None:
        """Hiện cửa sổ prompt Plan Episode để user copy."""
        selected_items = self.chapter_list.selectedItems()
        if not selected_items or not self.app_state.project:
            QMessageBox.warning(self, "Cảnh báo", "Hãy chọn ít nhất một chương.")
            return

        try:
            chapter_id = selected_items[0].data(ITEM_ROLE)
            service = ManualAIService(self.project_controller.project_service)
            exported = service.export_prompt(
                self.app_state.project,
                step="plan-episode",
                chapter_id=chapter_id,
                tone=self._tone_map[self.tone_combo.currentText()],
                density=self._density_map[self.density_combo.currentText()],
            )
            prompt_text = service.format_prompt_for_clipboard(exported)

            dialog = PromptExportDialog(prompt_text, "Lập kế hoạch tập", self)
            dialog.exec()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_import_plan(self) -> None:
        """Hiện cửa sổ paste JSON Plan Episode result."""
        selected_items = self.chapter_list.selectedItems()
        if not selected_items or not self.app_state.project:
            QMessageBox.warning(self, "Cảnh báo", "Hãy chọn ít nhất một chương.")
            return

        dialog = ResultImportDialog("Lập kế hoạch tập", self)
        if dialog.exec() == QDialog.Accepted:
            result_data = dialog.get_result_data()
            if result_data is None:
                return
            try:
                chapter_id = selected_items[0].data(ITEM_ROLE)
                service = ManualAIService(self.project_controller.project_service)
                message = service.import_result(
                    self.app_state.project,
                    step="plan-episode",
                    result_data=result_data,
                    chapter_id=chapter_id,
                    tone=self._tone_map[self.tone_combo.currentText()],
                    density=self._density_map[self.density_combo.currentText()],
                )
                QMessageBox.information(self, "Thông báo", message)
                self.refresh_callback()
            except Exception as exc:
                QMessageBox.critical(self, "Lỗi", str(exc))
