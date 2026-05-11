"""Tab for previewing all beats in an episode."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QApplication,
)

if TYPE_CHECKING:
    from app.controllers.generation_controller import GenerationController
    from app.ui.app_state import AppState

ITEM_ROLE = Qt.ItemDataRole.UserRole
ROW_HEIGHT = 120


class BeatPreviewTab(QWidget):
    def __init__(
        self,
        app_state: AppState,
        generation_controller: GenerationController,
        refresh_callback: callable,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.generation_controller = generation_controller
        self.refresh_callback = refresh_callback

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Top toolbar
        toolbar = QHBoxLayout()

        toolbar.addWidget(QLabel("Tập truyện:"))
        self.episode_combo = QComboBox()
        self.episode_combo.setMinimumWidth(250)
        self.episode_combo.currentIndexChanged.connect(self._on_episode_changed)
        toolbar.addWidget(self.episode_combo)

        toolbar.addWidget(QLabel("Phân cảnh:"))
        self.scene_combo = QComboBox()
        self.scene_combo.setMinimumWidth(200)
        self.scene_combo.currentIndexChanged.connect(self._on_scene_filter_changed)
        toolbar.addWidget(self.scene_combo)

        toolbar.addStretch()

        self.btn_refresh = QPushButton("Làm mới")
        self.btn_refresh.clicked.connect(self.refresh)
        toolbar.addWidget(self.btn_refresh)

        layout.addLayout(toolbar)

        # Main table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["STT", "PHÂN CẢNH", "NỘI DUNG", "PROMPT ẢNH"])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        self.table.setWordWrap(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.table)

    def refresh(self) -> None:
        """Refresh content from AppState."""
        if not self.app_state.project:
            self.table.setRowCount(0)
            self.episode_combo.clear()
            self.scene_combo.clear()
            return

        # 1. Update episode combo
        self.episode_combo.blockSignals(True)
        self.episode_combo.clear()
        selected_idx = 0
        for i, ep in enumerate(self.app_state.project.review_episodes):
            self.episode_combo.addItem(ep.title, ep.episode_id)
            if ep.episode_id == self.app_state.selected_episode_id:
                selected_idx = i

        if self.app_state.project.review_episodes:
            self.episode_combo.setCurrentIndex(selected_idx)
            if not self.app_state.selected_episode_id:
                self.app_state.selected_episode_id = self.app_state.project.review_episodes[
                    selected_idx
                ].episode_id
        self.episode_combo.blockSignals(False)

        # 2. Update scene filter
        self._update_scene_filter()

        # 3. Populate table
        self._populate_table()

    def _update_scene_filter(self) -> None:
        self.scene_combo.blockSignals(True)
        current_scene_id = self.scene_combo.currentData()
        self.scene_combo.clear()
        self.scene_combo.addItem("Tất cả phân cảnh", None)

        if self.app_state.selected_episode_id:
            try:
                episode = self.generation_controller.find_episode(
                    self.app_state.project, self.app_state.selected_episode_id
                )
                for scene in episode.scenes:
                    self.scene_combo.addItem(scene.title, scene.scene_id)
            except LookupError:
                pass

        # Restore selection if possible
        for i in range(self.scene_combo.count()):
            if self.scene_combo.itemData(i) == current_scene_id:
                self.scene_combo.setCurrentIndex(i)
                break

        self.scene_combo.blockSignals(False)

    def _populate_table(self) -> None:
        self.table.setRowCount(0)
        if not self.app_state.project or not self.app_state.selected_episode_id:
            return

        try:
            episode = self.generation_controller.find_episode(
                self.app_state.project, self.app_state.selected_episode_id
            )
        except LookupError:
            return

        filter_scene_id = self.scene_combo.currentData()

        all_rows = []
        for scene in episode.scenes:
            if filter_scene_id and scene.scene_id != filter_scene_id:
                continue

            for beat in scene.ordered_beats():
                all_rows.append((scene, beat))

        self.table.setRowCount(len(all_rows))
        for i, (scene, beat) in enumerate(all_rows):
            # STT - Centered
            stt_item = QTableWidgetItem(str(i + 1))
            stt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 0, stt_item)

            # PHÂN CẢNH
            self.table.setItem(i, 1, QTableWidgetItem(scene.title or scene.scene_id))

            # NỘI DUNG - Scrollable
            content = beat.review_text or "(Chưa có nội dung review)"
            content_edit = QPlainTextEdit(content)
            content_edit.setReadOnly(True)
            content_edit.setMaximumHeight(ROW_HEIGHT - 10)
            self.table.setCellWidget(i, 2, content_edit)

            # PROMPT ẢNH - Scrollable + Copy Button
            img_p = beat.image_prompt or ""
            neg_p = beat.negative_prompt or ""
            combined_prompt = f"{img_p}, negative prompt: {neg_p}" if img_p or neg_p else ""
            
            prompt_container = QWidget()
            prompt_layout = QVBoxLayout(prompt_container)
            prompt_layout.setContentsMargins(2, 2, 2, 2)
            prompt_layout.setSpacing(2)
            
            prompt_edit = QPlainTextEdit(combined_prompt)
            prompt_edit.setReadOnly(True)
            prompt_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            prompt_layout.addWidget(prompt_edit)
            
            btn_copy = QPushButton("Copy Prompt")
            btn_copy.clicked.connect(lambda checked=False, p=combined_prompt: self._copy_to_clipboard(p))
            prompt_layout.addWidget(btn_copy)
            
            self.table.setCellWidget(i, 3, prompt_container)
            
            # Fixed Row Height
            self.table.setRowHeight(i, ROW_HEIGHT)

    def _copy_to_clipboard(self, text: str) -> None:
        """Helper to copy text to system clipboard."""
        cb = QApplication.clipboard()
        cb.setText(text, mode=cb.Mode.Clipboard)

    def _on_episode_changed(self, index: int) -> None:
        episode_id = self.episode_combo.itemData(index)
        if episode_id and episode_id != self.app_state.selected_episode_id:
            self.app_state.selected_episode_id = episode_id
            self.refresh_callback()  # Refresh other tabs too

    def _on_scene_filter_changed(self, index: int) -> None:
        self._populate_table()
