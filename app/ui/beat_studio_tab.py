"""Main workspace for scene and beat editing.

Reworked in the UI redesign PR to use a Boords-style panel grid (default) plus
a fallback table view. Both views read from the same scene/beat selection so
the inspector form stays in sync regardless of which view is active.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
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

from app.ui.beat_card_delegate import (
    CARD_DATA_ROLE,
    CARD_HEIGHT,
    CARD_WIDTH,
    BeatCardData,
    BeatCardDelegate,
)
from app.ui.manual_ai_dialogs import PromptExportDialog, ResultImportDialog
from app.services.continuity_tag_service import ContinuityTagService

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

    FIELD_GROUPS: list[tuple[str, list[str]]] = [
        ("Narration", ["review_text", "visual_description"]),
        ("Prompt", ["image_prompt", "negative_prompt"]),
        ("Context", ["characters", "location", "emotion", "shot_type", "continuity_tags"]),
    ]

    VIEW_GRID = "grid"
    VIEW_TABLE = "table"

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
        self.view_mode: str = self.VIEW_GRID
        self._current_beats: list[Beat] = []
        self.tag_service = ContinuityTagService()
        self._build_ui()

    # =========================================================================
    # UI construction
    # =========================================================================
    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Header (Episode selector + view toggle)
        header_row = QHBoxLayout()
        
        self.episode_combo = QComboBox()
        self.episode_combo.setObjectName("episode-selector")
        self.episode_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.episode_combo.setMinimumHeight(32)
        header_row.addWidget(self.episode_combo, 1)

        self.btn_view_grid = QPushButton("⊞  Grid")
        self.btn_view_grid.setObjectName("view-toggle")
        self.btn_view_grid.setCheckable(True)
        self.btn_view_grid.setChecked(True)
        self.btn_view_table = QPushButton("☰  Table")
        self.btn_view_table.setObjectName("view-toggle")
        self.btn_view_table.setCheckable(True)
        header_row.addWidget(self.btn_view_grid)
        header_row.addWidget(self.btn_view_table)
        main_layout.addLayout(header_row)

        # Manual AI workflow card
        self.manual_group = QWidget()
        self.manual_group.setObjectName("manual-ai-card")
        manual_layout = QHBoxLayout(self.manual_group)
        manual_layout.setContentsMargins(12, 10, 12, 10)
        manual_layout.setSpacing(10)

        manual_title = QLabel("Quy trình AI")
        manual_title.setObjectName("manual-ai-title")
        manual_layout.addWidget(manual_title)

        self.manual_step_combo = QComboBox()
        self.manual_step_combo.addItem(
            "Tạo gói nhịp truyện đầy đủ (Khuyên dùng)", "generate-unified-package"
        )
        self.manual_step_combo.addItem("Chỉ tạo nhịp truyện", "generate-beats")
        self.manual_step_combo.addItem("Chỉ viết lại Review", "rewrite-review")
        self.manual_step_combo.addItem("Chỉ xây dựng Prompt ảnh", "build-prompts")
        manual_layout.addWidget(self.manual_step_combo, 1)

        self.btn_export_prompt = QPushButton("1. Lấy Prompt")
        self.btn_export_prompt.setObjectName("primary")
        self.btn_import_result = QPushButton("2. Dán kết quả / Áp dụng")
        self.btn_import_result.setObjectName("success")
        manual_layout.addWidget(self.btn_export_prompt)
        manual_layout.addWidget(self.btn_import_result)
        main_layout.addWidget(self.manual_group)

        # Advanced (hidden) action bar — kept for backwards compatibility with
        # any developer flows that still reach for these buttons.
        self.advanced_action_widget = QWidget()
        action_layout = QHBoxLayout(self.advanced_action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_gen_package = QPushButton("Tạo Gói Beat (Offline)")
        self.btn_gen_beats = QPushButton("Chỉ tạo nhịp (Plan Only)")
        self.btn_gen_review = QPushButton("Chỉ viết Review")
        self.btn_gen_prompts = QPushButton("Chỉ xây dựng Prompt")
        action_layout.addWidget(self.btn_gen_package)
        action_layout.addWidget(self.btn_gen_beats)
        action_layout.addWidget(self.btn_gen_review)
        action_layout.addWidget(self.btn_gen_prompts)
        self.advanced_action_widget.setVisible(False)
        main_layout.addWidget(self.advanced_action_widget)

        # 3-pane splitter: scenes / beats / inspector
        splitter = QSplitter(Qt.Orientation.Horizontal)

        scene_widget = self._build_scene_pane()
        splitter.addWidget(scene_widget)
        beats_widget = self._build_beats_pane()
        splitter.addWidget(beats_widget)
        inspector_widget = self._build_inspector_pane()
        splitter.addWidget(inspector_widget)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 2)
        splitter.setSizes([240, 720, 360])
        main_layout.addWidget(splitter, 1)

        # Signals
        self.scene_list.currentItemChanged.connect(self._on_scene_select)
        self.beat_table.itemSelectionChanged.connect(self._on_table_beat_select)
        self.beat_grid.itemSelectionChanged.connect(self._on_grid_beat_select)
        self.btn_save_beat.clicked.connect(self._on_save_beat)
        self.btn_export_prompt.clicked.connect(self._on_prompt)
        self.btn_import_result.clicked.connect(self._on_import)
        self.btn_delete_scene.clicked.connect(self._on_delete_scene)
        self.btn_delete_beat.clicked.connect(self._on_delete_beat)
        self.btn_view_table.clicked.connect(lambda: self.set_view_mode(self.VIEW_TABLE))
        self.episode_combo.currentIndexChanged.connect(self._on_episode_combo_changed)

    def _build_scene_pane(self) -> QWidget:
        wrapper = QFrame()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        heading = QLabel("Phân cảnh (Scenes)")
        heading.setObjectName("section-heading")
        layout.addWidget(heading)

        self.scene_list = QListWidget()
        self.scene_list.setObjectName("scene-list")
        layout.addWidget(self.scene_list, 1)

        self.btn_delete_scene = QPushButton("Xóa phân cảnh")
        self.btn_delete_scene.setObjectName("danger")
        layout.addWidget(self.btn_delete_scene)
        return wrapper

    def _build_beats_pane(self) -> QWidget:
        wrapper = QFrame()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        heading = QLabel("Nhịp truyện (Beats)")
        heading.setObjectName("section-heading")
        layout.addWidget(heading)

        self.beats_stack = QStackedWidget()

        # Grid view (default)
        self.beat_grid = QListWidget()
        self.beat_grid.setObjectName("beat-grid")
        self.beat_grid.setViewMode(QListView.ViewMode.IconMode)
        self.beat_grid.setResizeMode(QListView.ResizeMode.Adjust)
        self.beat_grid.setMovement(QListView.Movement.Static)
        self.beat_grid.setSpacing(8)
        self.beat_grid.setUniformItemSizes(True)
        self.beat_grid.setGridSize(QSize(CARD_WIDTH + 12, CARD_HEIGHT + 12))
        self.beat_grid.setMouseTracking(True)
        self.beat_grid.setItemDelegate(BeatCardDelegate(self.beat_grid))
        self.beats_stack.addWidget(self.beat_grid)

        # Table view (legacy)
        self.beat_table = QTableWidget(0, 3)
        self.beat_table.setHorizontalHeaderLabels(["ID", "Chức năng", "Nội dung"])
        self.beat_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.beat_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.beat_table.verticalHeader().setVisible(False)
        self.beats_stack.addWidget(self.beat_table)

        layout.addWidget(self.beats_stack, 1)

        self.btn_delete_beat = QPushButton("Xóa nhịp truyện")
        self.btn_delete_beat.setObjectName("danger")
        layout.addWidget(self.btn_delete_beat)

        return wrapper

    def _build_inspector_pane(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setObjectName("inspector")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(12, 12, 12, 12)
        inner_layout.setSpacing(10)

        heading = QLabel("Chi tiết nhịp truyện")
        heading.setObjectName("inspector-heading")
        inner_layout.addWidget(heading)

        for group_label, field_names in self.FIELD_GROUPS:
            group = QGroupBox(group_label)
            grid = QGridLayout(group)
            grid.setContentsMargins(10, 18, 10, 10)
            grid.setHorizontalSpacing(8)
            grid.setVerticalSpacing(6)

            for row, name in enumerate(field_names):
                label = QLabel(self.FIELD_LABELS.get(name, name))
                label.setObjectName("field-label")
                grid.addWidget(label, row * 2, 0)

                if name in self.MULTILINE_FIELDS:
                    widget: QWidget = QPlainTextEdit()
                    widget.setMaximumHeight(110)
                elif name == "emotion":
                    widget = QComboBox()
                    widget.setEditable(True)
                    widget.addItems(
                        ["neutral", "happy", "sad", "angry", "surprised", "tense", "mysterious"]
                    )
                elif name == "location":
                    widget = QComboBox()
                    widget.setEditable(True)
                else:
                    widget = QLineEdit()

                grid.addWidget(widget, row * 2 + 1, 0)
                self.fields[name] = widget

            inner_layout.addWidget(group)

        self.btn_save_beat = QPushButton("Lưu nhịp truyện")
        self.btn_save_beat.setObjectName("primary")
        self.btn_save_beat.setEnabled(False)
        inner_layout.addWidget(self.btn_save_beat)
        inner_layout.addStretch(1)

        scroll.setWidget(inner)
        return scroll

    # =========================================================================
    # View-mode toggling
    # =========================================================================
    def set_view_mode(self, mode: str) -> None:
        if mode not in (self.VIEW_GRID, self.VIEW_TABLE):
            return
        self.view_mode = mode
        is_grid = mode == self.VIEW_GRID
        self.btn_view_grid.setChecked(is_grid)
        self.btn_view_table.setChecked(not is_grid)
        self.beats_stack.setCurrentIndex(0 if is_grid else 1)
        self._sync_selection_to_views()

    # =========================================================================
    # Refresh / data binding
    # =========================================================================
    def refresh(self) -> None:
        # 1. Update Episode Combo
        self._block_signals(True)
        self.episode_combo.clear()
        
        project = self.app_state.project
        if not project:
            self.episode_combo.addItem("Chưa mở dự án", None)
            self.episode_combo.setEnabled(False)
        elif not project.review_episodes:
            self.episode_combo.addItem("Chưa có tập truyện — hãy tạo tại tab 'Kế hoạch tập'", None)
            self.episode_combo.setEnabled(False)
        else:
            self.episode_combo.setEnabled(True)
            selected_idx = -1
            for i, ep in enumerate(project.review_episodes):
                text = f"Tập: {ep.title} | Scenes: {len(ep.scenes)}"
                self.episode_combo.addItem(text, ep.episode_id)
                if ep.episode_id == self.app_state.selected_episode_id:
                    selected_idx = i
            
            if selected_idx >= 0:
                self.episode_combo.setCurrentIndex(selected_idx)
            else:
                # Fallback to first episode if current selection invalid
                self.episode_combo.setCurrentIndex(0)
                self.app_state.selected_episode_id = self.episode_combo.currentData()
        
        self._block_signals(False)

        # 2. Refresh lists based on selection
        self.scene_list.clear()
        self._clear_beats_views()
        self._clear_editor()

        if self.app_state.selected_episode_id and project:
            try:
                episode = self.generation_controller.find_episode(
                    project, self.app_state.selected_episode_id
                )
                
                # Populate scene list
                for scene in episode.scenes:
                    count = len(scene.beats) if hasattr(scene, "beats") else 0
                    item = QListWidgetItem(f"{scene.title}\n{count} nhịp")
                    item.setData(ITEM_ROLE, scene.scene_id)
                    self.scene_list.addItem(item)
                    if scene.scene_id == self.app_state.selected_scene_id:
                        self.scene_list.setCurrentItem(item)
                        self._load_beats(scene)
                
                # If no scene selected but we have scenes, pick first one
                if not self.app_state.selected_scene_id and episode.scenes:
                    self.scene_list.setCurrentRow(0)
            except LookupError:
                self.app_state.selected_episode_id = None

        has_ep = self.app_state.selected_episode_id is not None
        self.btn_export_prompt.setEnabled(has_ep)
        self.btn_import_result.setEnabled(has_ep)

        # Keep advanced buttons disabled if they were visible
        self.btn_gen_package.setEnabled(False)
        self.btn_gen_beats.setEnabled(False)

        has_beats = self._beat_count() > 0
        self.btn_gen_review.setEnabled(has_beats)
        self.btn_gen_prompts.setEnabled(has_beats)
        self.btn_save_beat.setEnabled(self.app_state.selected_beat_id is not None)

        # Refresh location combo box items
        if self.app_state.project:
            loc_combo = self.fields.get("location")
            if isinstance(loc_combo, QComboBox):
                current_text = loc_combo.currentText()
                loc_combo.clear()
                loc_names = [l.name for l in self.app_state.project.locations]
                loc_combo.addItems(loc_names)
                loc_combo.setCurrentText(current_text)

    def _beat_count(self) -> int:
        return (
            self.beat_table.rowCount()
            if self.view_mode == self.VIEW_TABLE
            else self.beat_grid.count()
        )

    def _clear_beats_views(self) -> None:
        self.beat_table.setRowCount(0)
        self.beat_grid.clear()
        self._current_beats = []

    def _load_beats(self, scene) -> None:
        beats = scene.ordered_beats()
        self._current_beats = list(beats)

        # Populate table view
        self.beat_table.setRowCount(len(beats))
        for row, beat in enumerate(beats):
            self.beat_table.setItem(row, 0, QTableWidgetItem(beat.beat_id))
            self.beat_table.setItem(row, 1, QTableWidgetItem(beat.story_function))
            preview = beat.review_text or beat.action or ""
            if len(preview) > 60:
                preview = preview[:57] + "..."
            self.beat_table.setItem(row, 2, QTableWidgetItem(preview))
            self.beat_table.item(row, 0).setData(ITEM_ROLE, beat.beat_id)

        # Populate grid view
        self.beat_grid.clear()
        for beat in beats:
            card = _build_card_data(beat)
            item = QListWidgetItem()
            item.setData(ITEM_ROLE, beat.beat_id)
            item.setData(CARD_DATA_ROLE, card)
            item.setSizeHint(QSize(CARD_WIDTH, CARD_HEIGHT))
            self.beat_grid.addItem(item)

        self._sync_selection_to_views()

    def _sync_selection_to_views(self) -> None:
        if not self.app_state.selected_beat_id:
            return
        # Table
        for row in range(self.beat_table.rowCount()):
            item = self.beat_table.item(row, 0)
            if item and item.data(ITEM_ROLE) == self.app_state.selected_beat_id:
                self.beat_table.selectRow(row)
                break
        # Grid
        for i in range(self.beat_grid.count()):
            item = self.beat_grid.item(i)
            if item and item.data(ITEM_ROLE) == self.app_state.selected_beat_id:
                self.beat_grid.setCurrentItem(item)
                break

    def _load_beat_data(self, beat: Beat) -> None:
        project = self.app_state.project
        ps = self.generation_controller.project_service # Access project service for resolution

        for name in self.FIELD_NAMES:
            value = getattr(beat, name)
            
            # Resolve ID to Name for display
            display_value = ""
            if name == "characters" and project:
                char_ids = value if isinstance(value, list) else []
                names = [ps.character_display_name(project, cid) for cid in char_ids]
                display_value = ", ".join(names)
            elif name == "location" and project:
                display_value = ps.location_display_name(project, value)
            elif name == "continuity_tags" and project:
                tags = value if isinstance(value, list) else []
                names = self.tag_service.to_display_names(project, tags)
                display_value = ", ".join(names)
            else:
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

    # =========================================================================
    # Signal handlers
    # =========================================================================
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
            self._clear_beats_views()

    def _on_table_beat_select(self) -> None:
        ranges = self.beat_table.selectedRanges()
        if not ranges:
            return
        row = ranges[0].topRow()
        item = self.beat_table.item(row, 0)
        if item is None:
            return
        self._set_selected_beat(item.data(ITEM_ROLE))

    def _on_grid_beat_select(self) -> None:
        current = self.beat_grid.currentItem()
        if current is None:
            return
        self._set_selected_beat(current.data(ITEM_ROLE))

    def _on_episode_combo_changed(self, index: int) -> None:
        if index < 0: return
        ep_id = self.episode_combo.itemData(index)
        if ep_id != self.app_state.selected_episode_id:
            self.app_state.selected_episode_id = ep_id
            self.app_state.selected_scene_id = None # Reset scene when changing episode
            self.app_state.selected_beat_id = None
            self.refresh()

    def _set_selected_beat(self, beat_id: str | None) -> None:
        if not beat_id:
            self.app_state.selected_beat_id = None
            self._clear_editor()
            self.btn_save_beat.setEnabled(False)
            return
        self.app_state.selected_beat_id = beat_id
        beat = self._find_beat(beat_id)
        if beat is not None:
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

        values: dict[str, str] = {}
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
                project = self.app_state.project
                ps = self.generation_controller.project_service

                # Resolve Name back to ID before saving
                if "characters" in values and project:
                    names = [n.strip() for n in values["characters"].split(",") if n.strip()]
                    ids = [ps.resolve_character_id(project, n) for n in names]
                    values["characters"] = ids
                
                if "location" in values and project:
                    values["location"] = ps.resolve_location_id(project, values["location"])

                if "continuity_tags" in values and project:
                    values["continuity_tags"] = self.tag_service.resolve_display_names(project, values["continuity_tags"])

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
            # Store current selection to restore after refresh
            prev_ep = self.app_state.selected_episode_id
            prev_sc = self.app_state.selected_scene_id
            prev_beat = self.app_state.selected_beat_id

            dialog = ResultImportDialog(step_label, self)
            if dialog.exec() and dialog.result_data is not None:
                message = self.manual_ai_controller.import_result(
                    self.app_state.project,
                    step=step,
                    result_data=dialog.result_data,
                    episode_id=self.app_state.selected_episode_id,
                    chapter_id=self.app_state.selected_scene_id,
                )
                
                # Restore selection if still valid
                self.app_state.selected_episode_id = prev_ep
                self.app_state.selected_scene_id = prev_sc
                self.app_state.selected_beat_id = prev_beat
                
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
            f"Bạn có chắc muốn xóa phân cảnh '{scene_id}'?\n"
            "Tất cả beats trong phân cảnh này sẽ bị xóa.\nHành động này không thể hoàn tác.",
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
            f"Bạn có chắc muốn xóa nhịp truyện '{beat_id}'?\n" "Hành động này không thể hoàn tác.",
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

    def _block_signals(self, block: bool) -> None:
        self.episode_combo.blockSignals(block)
        self.scene_list.blockSignals(block)
        self.beat_table.blockSignals(block)
        self.beat_grid.blockSignals(block)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _build_card_data(beat: Beat) -> BeatCardData:
    """Translate a domain :class:`Beat` into the flat payload the delegate paints."""
    selected = getattr(beat, "selected_image", None)
    image_path = getattr(selected, "image_path", None) if selected is not None else None
    preview = beat.review_text or getattr(beat, "action", "") or ""
    approved = (getattr(beat, "status", "") or "").lower() in {"approved", "ok"}
    return BeatCardData(
        beat_id=beat.beat_id,
        order_index=int(getattr(beat, "order_index", 0) or 0),
        review_preview=preview.strip(),
        image_path=image_path,
        has_review_text=bool((beat.review_text or "").strip()),
        has_image_prompt=bool((beat.image_prompt or "").strip()),
        has_image=bool(image_path),
        approved=approved,
    )
