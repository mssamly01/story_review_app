"""Main workspace for scene and beat editing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from app.controllers.generation_controller import GenerationController
    from app.controllers.manual_ai_controller import ManualAIController
    from app.domain.beat import Beat
    from app.ui.app_state import AppState

from app.ui.manual_ai_dialogs import PromptExportDialog, ResultImportDialog

ITEM_ROLE = Qt.ItemDataRole.UserRole


class BeatStudioTab(QWidget):
    FIELD_LABELS = {
        "review_text": "Nội dung Review",
        "visual_description": "Mô tả hình ảnh",
        "image_prompt": "Image Prompt",
        "negative_prompt": "Negative Prompt",
        "characters": "Nhân vật",
        "location": "Bối cảnh",
        "emotion": "Cảm xúc",
        "shot_type": "Góc máy",
        "continuity_tags": "Thẻ liên kết (Continuity)",
    }
    FIELD_NAMES = [
        "review_text",
        "visual_description",
        "image_prompt",
        "negative_prompt",
        "characters",
        "location",
        "emotion",
        "shot_type",
        "continuity_tags",
    ]
    MULTILINE_FIELDS = {"review_text", "visual_description", "image_prompt", "negative_prompt"}

    def __init__(
        self,
        app_state: AppState,
        generation_controller: GenerationController,
        manual_ai_controller: ManualAIController,
        refresh_callback: callable,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.generation_controller = generation_controller
        self.manual_ai_controller = manual_ai_controller
        self.refresh_callback = refresh_callback
        self.fields: dict[str, QWidget] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        # Context Label
        self.context_label = QLabel("Chưa chọn tập truyện — chọn tại tab 'Kế hoạch tập'")
        self.context_label.setStyleSheet(
            "font-weight: bold; padding: 4px; background: #f0f0f0; border-radius: 4px;"
        )
        main_layout.addWidget(self.context_label)

        # Action Bar (Hidden by default, used for advanced/dev mode)
        self.advanced_action_widget = QWidget()
        action_layout = QHBoxLayout(self.advanced_action_widget)
        self.btn_gen_package = QPushButton("Tạo Gói Beat (Offline)")
        self.btn_gen_beats = QPushButton("Chỉ tạo nhịp (Plan Only)")
        self.btn_gen_review = QPushButton("Chỉ viết Review")
        self.btn_gen_prompts = QPushButton("Chỉ xây dựng Prompt")
        action_layout.addWidget(self.btn_gen_package)
        action_layout.addWidget(self.btn_gen_beats)
        action_layout.addWidget(self.btn_gen_review)
        action_layout.addWidget(self.btn_gen_prompts)
        main_layout.addWidget(self.advanced_action_widget)
        self.advanced_action_widget.setVisible(False)  # Hide offline buttons

        # Primary Workflow: Manual AI Section
        manual_group = QWidget()
        manual_group.setStyleSheet("background: #e1f5fe; border-radius: 8px; padding: 10px;")
        manual_layout = QHBoxLayout(manual_group)

        self.manual_step_combo = QComboBox()
        self.manual_step_combo.addItem(
            "Tạo gói nhịp truyện đầy đủ (Khuyên dùng)", "generate-unified-package"
        )
        self.manual_step_combo.addItem("Chỉ tạo nhịp truyện", "generate-beats")
        self.manual_step_combo.addItem("Chỉ viết lại Review", "rewrite-review")
        self.manual_step_combo.addItem("Chỉ xây dựng Prompt ảnh", "build-prompts")

        self.btn_export_prompt = QPushButton("1. Lấy Prompt")
        self.btn_export_prompt.setStyleSheet(
            "background-color: #0288d1; color: white; font-weight: bold; padding: 6px;"
        )

        self.btn_import_result = QPushButton("2. Dán kết quả / Áp dụng")
        self.btn_import_result.setStyleSheet(
            "background-color: #388e3c; color: white; font-weight: bold; padding: 6px;"
        )

        manual_layout.addWidget(QLabel("<b>Quy trình AI:</b>"))
        manual_layout.addWidget(self.manual_step_combo, 1)
        manual_layout.addWidget(self.btn_export_prompt)
        manual_layout.addWidget(self.btn_import_result)
        main_layout.addWidget(manual_group)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 1. Scene List
        scene_widget = QWidget()
        scene_layout = QVBoxLayout(scene_widget)
        scene_layout.addWidget(QLabel("Phân cảnh (Scenes)"))
        self.scene_list = QListWidget()
        scene_layout.addWidget(self.scene_list)
        self.btn_delete_scene = QPushButton("Xóa phân cảnh")
        scene_layout.addWidget(self.btn_delete_scene)
        splitter.addWidget(scene_widget)

        # 2. Beat Table
        beat_widget = QWidget()
        beat_layout = QVBoxLayout(beat_widget)
        beat_layout.addWidget(QLabel("Nhịp truyện (Beats)"))
        self.beat_table = QTableWidget(0, 3)
        self.beat_table.setHorizontalHeaderLabels(["ID", "Chức năng", "Nội dung"])
        self.beat_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.beat_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        beat_layout.addWidget(self.beat_table)
        self.btn_delete_beat = QPushButton("Xóa nhịp truyện")
        beat_layout.addWidget(self.btn_delete_beat)
        splitter.addWidget(beat_widget)

        # 3. Beat Editor Form
        editor_scroll = QScrollArea()
        editor_scroll.setWidgetResizable(True)
        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        editor_layout.addWidget(QLabel("Chi tiết nhịp truyện"))

        self.form_layout = QGridLayout()
        for row, name in enumerate(self.FIELD_NAMES):
            label = QLabel(self.FIELD_LABELS.get(name, name))
            self.form_layout.addWidget(label, row, 0)
            if name in self.MULTILINE_FIELDS:
                widget = QPlainTextEdit()
                widget.setMaximumHeight(100)
            elif name == "emotion":
                widget = QComboBox()
                widget.setEditable(True)
                widget.addItems(
                    ["neutral", "happy", "sad", "angry", "surprised", "tense", "mysterious"]
                )
            else:
                widget = QLineEdit()

            self.form_layout.addWidget(widget, row, 1)
            self.fields[name] = widget

        editor_layout.addLayout(self.form_layout)
        self.btn_save_beat = QPushButton("Lưu nhịp truyện")
        editor_layout.addWidget(self.btn_save_beat)
        editor_layout.addStretch()

        editor_scroll.setWidget(editor_widget)
        splitter.addWidget(editor_scroll)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 2)
        main_layout.addWidget(splitter)

        # Connect signals
        self.scene_list.currentItemChanged.connect(self._on_scene_select)
        self.beat_table.itemSelectionChanged.connect(self._on_beat_select)
        self.btn_save_beat.clicked.connect(self._on_save_beat)
        self.btn_export_prompt.clicked.connect(self._on_prompt)
        self.btn_import_result.clicked.connect(self._on_import)
        self.btn_delete_scene.clicked.connect(self._on_delete_scene)
        self.btn_delete_beat.clicked.connect(self._on_delete_beat)

    def refresh(self) -> None:
        self.scene_list.clear()
        self.beat_table.setRowCount(0)
        self._clear_editor()

        if self.app_state.selected_episode_id and self.app_state.project:
            episode = self.generation_controller.find_episode(
                self.app_state.project, self.app_state.selected_episode_id
            )
            self.context_label.setText(f"Tập: {episode.title} | Scenes: {len(episode.scenes)}")

            for scene in episode.scenes:
                item = QListWidgetItem(f"{scene.scene_id} | {scene.title}")
                item.setData(ITEM_ROLE, scene.scene_id)
                self.scene_list.addItem(item)
                if scene.scene_id == self.app_state.selected_scene_id:
                    self.scene_list.setCurrentItem(item)
                    self._load_beats(scene)
        else:
            self.context_label.setText("Chưa chọn tập truyện — chọn tại tab 'Kế hoạch tập'")

        has_ep = self.app_state.selected_episode_id is not None
        self.btn_export_prompt.setEnabled(has_ep)
        self.btn_import_result.setEnabled(has_ep)

        # Keep advanced buttons disabled if they were visible
        self.btn_gen_package.setEnabled(False)
        self.btn_gen_beats.setEnabled(False)

        has_beats = self.beat_table.rowCount() > 0
        self.btn_gen_review.setEnabled(has_beats)
        self.btn_gen_prompts.setEnabled(has_beats)
        self.btn_save_beat.setEnabled(self.app_state.selected_beat_id is not None)

    def _load_beats(self, scene) -> None:
        beats = scene.ordered_beats()
        self.beat_table.setRowCount(len(beats))
        for row, beat in enumerate(beats):
            self.beat_table.setItem(row, 0, QTableWidgetItem(beat.beat_id))
            self.beat_table.setItem(row, 1, QTableWidgetItem(beat.story_function))
            preview = beat.review_text or beat.action or ""
            if len(preview) > 50:
                preview = preview[:47] + "..."
            self.beat_table.setItem(row, 2, QTableWidgetItem(preview))

            # Store ID in the first cell
            self.beat_table.item(row, 0).setData(ITEM_ROLE, beat.beat_id)

            if beat.beat_id == self.app_state.selected_beat_id:
                self.beat_table.selectRow(row)
                self._load_beat_data(beat)

    def _load_beat_data(self, beat: Beat) -> None:
        for name in self.FIELD_NAMES:
            value = getattr(beat, name)
            display_value = ", ".join(value) if isinstance(value, list) else str(value or "")
            widget = self.fields[name]
            if isinstance(widget, QPlainTextEdit):
                widget.setPlainText(display_value)
            elif isinstance(widget, QComboBox):
                widget.setCurrentText(display_value)
            else:
                widget.setText(display_value)

    def _clear_editor(self) -> None:
        for widget in self.fields.values():
            if isinstance(widget, QPlainTextEdit):
                widget.clear()
            elif isinstance(widget, QComboBox):
                widget.setCurrentIndex(-1)
            else:
                widget.setText("")

    def _on_scene_select(self, current: QListWidgetItem | None, previous: object) -> None:
        if current and self.app_state.selected_episode_id:
            scene_id = current.data(ITEM_ROLE)
            self.app_state.selected_scene_id = scene_id
            scene = self.generation_controller.find_scene(
                self.app_state.project, self.app_state.selected_episode_id, scene_id
            )
            self._load_beats(scene)
        else:
            self.app_state.selected_scene_id = None
            self.beat_table.setRowCount(0)

    def _on_beat_select(self) -> None:
        ranges = self.beat_table.selectedRanges()
        if not ranges:
            self.app_state.selected_beat_id = None
            self._clear_editor()
            self.btn_save_beat.setEnabled(False)
            return

        row = ranges[0].topRow()
        beat_id = self.beat_table.item(row, 0).data(ITEM_ROLE)
        self.app_state.selected_beat_id = beat_id

        beat = self._find_beat(beat_id)
        if beat:
            self._load_beat_data(beat)
            self.btn_save_beat.setEnabled(True)

    def _find_beat(self, beat_id: str) -> Beat | None:
        if not self.app_state.project:
            return None
        for ep in self.app_state.project.review_episodes:
            for sc in ep.scenes:
                for b in sc.beats:
                    if b.beat_id == beat_id:
                        return b
        return None

    def _on_save_beat(self) -> None:
        if not self.app_state.selected_beat_id:
            return

        values = {}
        for name, widget in self.fields.items():
            if isinstance(widget, QPlainTextEdit):
                values[name] = widget.toPlainText()
            elif isinstance(widget, QComboBox):
                values[name] = widget.currentText()
            else:
                values[name] = widget.text()

        try:
            beat = self._find_beat(self.app_state.selected_beat_id)
            if beat:
                self.generation_controller.update_beat_fields(beat, **values)
                self.app_state.project.touch()
                QMessageBox.information(self, "Thông báo", "Đã lưu nhịp truyện.")
                self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_prompt(self) -> None:
        """Hiện cửa sổ prompt cho step đã chọn từ dropdown."""
        if not self.app_state.project or not self.app_state.selected_episode_id:
            QMessageBox.warning(self, "Cảnh báo", "Hãy chọn tập truyện trước.")
            return

        step = self.manual_step_combo.currentData()
        step_label = self.manual_step_combo.currentText()

        try:
            prompt_text = self.manual_ai_controller.export_prompt(
                self.app_state.project,
                step=step,
                episode_id=self.app_state.selected_episode_id,
                chapter_id=self.app_state.selected_scene_id,
            )
            dialog = PromptExportDialog(prompt_text, step_label, self)
            dialog.exec()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_import(self) -> None:
        """Hiện cửa sổ paste JSON result cho step đã chọn từ dropdown."""
        if not self.app_state.project or not self.app_state.selected_episode_id:
            QMessageBox.warning(self, "Cảnh báo", "Hãy chọn tập truyện trước.")
            return

        step = self.manual_step_combo.currentData()
        step_label = self.manual_step_combo.currentText()

        try:
            dialog = ResultImportDialog(step_label, self)
            if dialog.exec() and dialog.result_data is not None:
                message = self.manual_ai_controller.import_result(
                    self.app_state.project,
                    step=step,
                    result_data=dialog.result_data,
                    episode_id=self.app_state.selected_episode_id,
                )
                QMessageBox.information(self, "Thông báo", message)
                self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_delete_scene(self) -> None:
        """Xóa phân cảnh đang chọn khỏi episode."""
        if (
            not self.app_state.project
            or not self.app_state.selected_episode_id
            or not self.app_state.selected_scene_id
        ):
            QMessageBox.warning(self, "Cảnh báo", "Hãy chọn phân cảnh cần xóa.")
            return

        scene_id = self.app_state.selected_scene_id
        reply = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa phân cảnh '{scene_id}'?\nTất cả beats trong phân cảnh này sẽ bị xóa.\nHành động này không thể hoàn tác.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        episode = self.generation_controller.find_episode(
            self.app_state.project, self.app_state.selected_episode_id
        )
        episode.scenes = [sc for sc in episode.scenes if sc.scene_id != scene_id]
        self.app_state.project.touch()
        self.app_state.selected_scene_id = None
        self.app_state.selected_beat_id = None
        self.refresh_callback()

    def _on_delete_beat(self) -> None:
        """Xóa nhịp truyện đang chọn khỏi scene."""
        if (
            not self.app_state.project
            or not self.app_state.selected_episode_id
            or not self.app_state.selected_scene_id
            or not self.app_state.selected_beat_id
        ):
            QMessageBox.warning(self, "Cảnh báo", "Hãy chọn nhịp truyện cần xóa.")
            return

        beat_id = self.app_state.selected_beat_id
        reply = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa nhịp truyện '{beat_id}'?\nHành động này không thể hoàn tác.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        scene = self.generation_controller.find_scene(
            self.app_state.project,
            self.app_state.selected_episode_id,
            self.app_state.selected_scene_id,
        )
        scene.beats = [b for b in scene.beats if b.beat_id != beat_id]
        self.app_state.project.touch()
        self.app_state.selected_beat_id = None
        self._clear_editor()
        self.refresh_callback()
