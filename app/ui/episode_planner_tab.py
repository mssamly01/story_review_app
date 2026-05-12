"""Episode planner tab."""

from __future__ import annotations

import json
import re
from app.services.continuity_tag_service import ContinuityTagService
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from app.controllers.batch_workflow_controller import BatchWorkflowController
    from app.controllers.generation_controller import GenerationController
    from app.controllers.manual_ai_controller import ManualAIController
    from app.controllers.project_controller import ProjectController
    from app.domain.beat import Beat
    from app.domain.episode import ReviewEpisode
    from app.domain.scene import Scene
    from app.ui.app_state import AppState

ITEM_ROLE = Qt.ItemDataRole.UserRole
ITEM_TYPE_ROLE = Qt.ItemDataRole.UserRole + 1
SCENE_ROLE = Qt.ItemDataRole.UserRole + 2
BEAT_ROLE = Qt.ItemDataRole.UserRole + 3


class EpisodePlannerTab(QWidget):
    """Manual AI workflow for episode planning, beats, and review text."""

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
            "Bí ẩn": "mysterious",
            "Kịch tính": "dramatic",
            "Trung lập": "neutral",
            "Hài hước": "humorous",
            "Nhanh": "fast-paced",
        }
        self._density_map = {
            "Đầy đủ": "full",
            "Cân bằng": "balanced",
            "Tóm gọn": "condensed",
        }

        self._density_map = {
            "Ngắn: 30-45 beat": "short",
            "Cân bằng: 50-70 beat": "balanced",
            "Đầy đủ: 80-110 beat": "full",
            "Siêu chi tiết: 110-150 beat": "ultra_detailed",
        }

        self._refreshing = False
        self.tag_service = ContinuityTagService()
        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self.setup_group = QGroupBox("Episode Setup")
        setup_layout = QGridLayout(self.setup_group)
        setup_layout.setContentsMargins(5, 2, 5, 2)
        setup_layout.setSpacing(5)
        self._build_setup_section(setup_layout)
        main_layout.addWidget(self.setup_group)

        self.prompt_workflow_group = QGroupBox("Manual AI Prompt Workflow")
        workflow_layout = QVBoxLayout(self.prompt_workflow_group)
        workflow_layout.setContentsMargins(5, 5, 5, 2)
        workflow_layout.setSpacing(2)
        self._build_prompt_workflow_section(workflow_layout)
        main_layout.addWidget(self.prompt_workflow_group, 1)

        self.structure_preview_group = QGroupBox("Episode Structure Preview")
        preview_layout = QVBoxLayout(self.structure_preview_group)
        self._build_structure_preview_section(preview_layout)
        main_layout.addWidget(self.structure_preview_group, 6)

        self.btn_delete_episode.clicked.connect(self._on_delete_episode)
        self.btn_prompt_plan.clicked.connect(self._on_prompt_plan)
        self.btn_copy_prompt.clicked.connect(self._on_copy_prompt)
        self.btn_import_plan.clicked.connect(self._on_import_plan)
        self.btn_save_beat_text.clicked.connect(self._on_save_beat_text_changes)
        self.chapter_list.itemSelectionChanged.connect(self._on_chapter_selection_changed)
        self.episode_list.currentItemChanged.connect(self._on_episode_select)
        self.scene_tree.itemSelectionChanged.connect(self._on_structure_item_select)
        self.scene_tree.itemClicked.connect(self._on_tree_item_clicked)

    def _build_setup_section(self, layout: QGridLayout) -> None:
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)

        self.title_edit = QLineEdit("Tập 1")
        self.tone_combo = QComboBox()
        self.tone_combo.addItems(list(self._tone_map.keys()))
        self.density_combo = QComboBox()
        self.density_combo.addItems(list(self._density_map.keys()))
        self.density_combo.setCurrentText("Đầy đủ: 80-110 beat")
        self.density_helper_label = QLabel(
            "Full: phù hợp review kể lại chi tiết, chương dài thường 80-110 beat."
        )
        self.density_helper_label.setStyleSheet("font-size: 10px; color: #888;")
        self.density_helper_label.setWordWrap(True)
        self.manual_task_combo = QComboBox()
        self.manual_task_combo.addItem(
            "Tạo kế hoạch tập + nhịp truyện + review text",
            "plan-episode-with-review",
        )
        self.manual_task_combo.addItem("Chỉ tạo kế hoạch tập", "plan-episode")
        self.manual_task_combo.addItem("Chỉ tạo nhịp truyện", "generate-beats")
        self.manual_task_combo.addItem("Chỉ viết lại review", "rewrite-review")

        form_layout.addRow("Episode title", self.title_edit)
        form_layout.addRow("Tone / narration_style", self.tone_combo)
        form_layout.addRow("Retelling density", self.density_combo)
        form_layout.addRow("", self.density_helper_label)
        form_layout.addRow("Target mode", self.manual_task_combo)
        layout.addWidget(form_widget, 0, 0)

        chapter_box = QGroupBox("Source chapter selector")
        chapter_layout = QVBoxLayout(chapter_box)
        self.chapter_list = QListWidget()
        self.chapter_list.setMaximumHeight(110)
        self.chapter_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        chapter_layout.addWidget(self.chapter_list)
        layout.addWidget(chapter_box, 0, 1)

        episode_box = QGroupBox("Episode selector")
        episode_layout = QVBoxLayout(episode_box)
        self.episode_list = QListWidget()
        self.episode_list.setMaximumHeight(110)
        episode_layout.addWidget(self.episode_list)
        self.btn_delete_episode = QPushButton("Xóa tập")
        episode_layout.addWidget(self.btn_delete_episode)
        layout.addWidget(episode_box, 0, 2)

        self.bible_status_group = QGroupBox("Bible / Style readiness")
        status_layout = QVBoxLayout(self.bible_status_group)
        self.lbl_status_char = QLabel("- Characters: -")
        self.lbl_status_loc = QLabel("- Locations: -")
        self.lbl_status_style = QLabel("- Styles: -")
        self.lbl_status_warning = QLabel("")
        self.lbl_status_warning.setWordWrap(True)
        self.lbl_status_warning.setStyleSheet("color: #b36b00;")
        status_layout.addWidget(self.lbl_status_char)
        status_layout.addWidget(self.lbl_status_loc)
        status_layout.addWidget(self.lbl_status_style)
        status_layout.addWidget(self.lbl_status_warning)
        layout.addWidget(self.bible_status_group, 0, 3)

        layout.setColumnStretch(0, 2)
        layout.setColumnStretch(1, 2)
        layout.setColumnStretch(2, 2)
        layout.setColumnStretch(3, 2)

    def _build_prompt_workflow_section(self, layout: QVBoxLayout) -> None:
        button_row = QHBoxLayout()
        self.btn_prompt_plan = QPushButton("Lấy Prompt Kế Hoạch Tập")
        self.btn_copy_prompt = QPushButton("Copy Prompt")
        self.btn_import_plan = QPushButton("Áp dụng Kết Quả")
        button_row.addWidget(self.btn_prompt_plan)
        button_row.addWidget(self.btn_copy_prompt)
        button_row.addStretch()
        button_row.addWidget(self.btn_import_plan)
        layout.addLayout(button_row)

        prompt_splitter = QSplitter(Qt.Orientation.Horizontal)

        prompt_box = QWidget()
        prompt_layout = QVBoxLayout(prompt_box)
        prompt_layout.setContentsMargins(0, 0, 0, 0)
        prompt_layout.addWidget(QLabel("Prompt preview"))
        self.prompt_preview = QPlainTextEdit()
        self.prompt_preview.setReadOnly(True)
        self.prompt_preview.setPlaceholderText("Prompt sẽ hiện ở đây để copy sang AI bên ngoài.")
        self.prompt_preview.setMinimumHeight(120)
        prompt_layout.addWidget(self.prompt_preview)

        result_box = QWidget()
        result_layout = QVBoxLayout(result_box)
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_layout.addWidget(QLabel("AI JSON result input"))
        self.result_input = QPlainTextEdit()
        self.result_input.setPlaceholderText("Dán JSON kết quả AI vào đây.")
        self.result_input.setMinimumHeight(120)
        result_layout.addWidget(self.result_input)

        prompt_splitter.addWidget(prompt_box)
        prompt_splitter.addWidget(result_box)
        prompt_splitter.setSizes([500, 500])
        layout.addWidget(prompt_splitter)

        self.apply_summary_label = QLabel("")
        self.apply_summary_label.setWordWrap(True)
        layout.addWidget(self.apply_summary_label)

    def _build_structure_preview_section(self, layout: QVBoxLayout) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)

        scene_box = QWidget()
        scene_layout = QVBoxLayout(scene_box)
        scene_layout.addWidget(QLabel("Screens / scenes and beats"))
        self.scene_tree = QTreeWidget()
        self.scene_tree.setColumnCount(4)
        self.scene_tree.setHeaderLabels(["Nội dung", "Chức năng", "Cảm xúc", "Góc máy"])
        header = self.scene_tree.header()
        from PySide6.QtWidgets import QHeaderView
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.scene_tree.setColumnWidth(1, 100)
        self.scene_tree.setColumnWidth(2, 100)
        self.scene_tree.setColumnWidth(3, 120)
        
        self.scene_tree.setMinimumWidth(460)
        self.scene_tree.setIndentation(20)
        self.scene_tree.setAnimated(True)
        self.scene_tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        scene_layout.addWidget(self.scene_tree)

        beat_box = QWidget()
        beat_layout = QVBoxLayout(beat_box)
        detail_group = QGroupBox("Selected beat text/story fields")
        detail_outer_layout = QVBoxLayout(detail_group)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        detail_container = QWidget()
        detail_layout = QVBoxLayout(detail_container)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(8)

        identity_group = QGroupBox("Identity")
        identity_layout = QFormLayout(identity_group)
        self.beat_id_edit = QLineEdit()
        self.beat_id_edit.setReadOnly(True)
        self.beat_scene_id_edit = QLineEdit()
        self.beat_scene_id_edit.setReadOnly(True)
        self.beat_order_index_edit = QLineEdit()
        self.beat_story_function_edit = QLineEdit()
        identity_layout.addRow("Beat ID", self.beat_id_edit)
        identity_layout.addRow("Scene ID", self.beat_scene_id_edit)
        identity_layout.addRow("Order Index", self.beat_order_index_edit)
        identity_layout.addRow("Story Function", self.beat_story_function_edit)
        detail_layout.addWidget(identity_group)

        story_group = QGroupBox("Review / Story")
        story_layout = QFormLayout(story_group)
        self.beat_action_edit = QLineEdit()
        self.beat_emotion_edit = QLineEdit()
        self.beat_visual_description_edit = QLineEdit()
        self.beat_review_text_edit = QPlainTextEdit()
        self.beat_review_text_edit.setMinimumHeight(120)
        story_layout.addRow("Action", self.beat_action_edit)
        story_layout.addRow("Emotion", self.beat_emotion_edit)
        story_layout.addRow("Visual Description", self.beat_visual_description_edit)
        story_layout.addRow("Review Text", self.beat_review_text_edit)
        detail_layout.addWidget(story_group)

        storyboard_group = QGroupBox("Storyboard / Image Planning")
        storyboard_layout = QFormLayout(storyboard_group)
        self.beat_camera_edit = QLineEdit()
        self.beat_shot_type_edit = QLineEdit()
        self.beat_time_of_day_edit = QLineEdit()
        self.beat_lighting_edit = QLineEdit()
        self.beat_atmosphere_edit = QLineEdit()
        self.beat_location_cues_edit = QLineEdit()
        self.beat_asmr_visuals_edit = QLineEdit()
        self.beat_composition_edit = QLineEdit()
        self.beat_posture_edit = QLineEdit()
        self.beat_expression_edit = QLineEdit()
        self.beat_body_language_edit = QLineEdit()
        storyboard_layout.addRow("Camera", self.beat_camera_edit)
        storyboard_layout.addRow("Shot Type", self.beat_shot_type_edit)
        storyboard_layout.addRow("Time of Day", self.beat_time_of_day_edit)
        storyboard_layout.addRow("Lighting", self.beat_lighting_edit)
        storyboard_layout.addRow("Atmosphere", self.beat_atmosphere_edit)
        storyboard_layout.addRow("Location Cues", self.beat_location_cues_edit)
        storyboard_layout.addRow("ASMR Visuals", self.beat_asmr_visuals_edit)
        storyboard_layout.addRow("Composition", self.beat_composition_edit)
        storyboard_layout.addRow("Posture", self.beat_posture_edit)
        storyboard_layout.addRow("Expression", self.beat_expression_edit)
        storyboard_layout.addRow("Body Language", self.beat_body_language_edit)
        detail_layout.addWidget(storyboard_group)

        refs_group = QGroupBox("References")
        refs_layout = QFormLayout(refs_group)
        self.beat_characters_edit = QLineEdit()
        self.beat_character_variants_edit = QLineEdit()
        self.beat_character_outfits_edit = QLineEdit()
        self.beat_location_edit = QLineEdit()
        self.beat_continuity_tags_edit = QLineEdit()
        self.beat_props_edit = QLineEdit()
        self.beat_wardrobe_notes_edit = QLineEdit()
        self.beat_character_state_edit = QLineEdit()
        self.beat_location_state_edit = QLineEdit()
        self.beat_transition_note_edit = QLineEdit()
        refs_layout.addRow("Characters", self.beat_characters_edit)
        refs_layout.addRow("Character Variants", self.beat_character_variants_edit)
        refs_layout.addRow("Character Outfits", self.beat_character_outfits_edit)
        refs_layout.addRow("Location", self.beat_location_edit)
        refs_layout.addRow("Continuity Tags", self.beat_continuity_tags_edit)
        refs_layout.addRow("Props", self.beat_props_edit)
        refs_layout.addRow("Wardrobe Notes", self.beat_wardrobe_notes_edit)
        refs_layout.addRow("Character State", self.beat_character_state_edit)
        refs_layout.addRow("Location State", self.beat_location_state_edit)
        refs_layout.addRow("Transition Note", self.beat_transition_note_edit)
        detail_layout.addWidget(refs_group)

        detail_layout.addStretch()
        scroll_area.setWidget(detail_container)
        detail_outer_layout.addWidget(scroll_area)
        self.btn_save_beat_text = QPushButton("Save Beat Text Changes")
        detail_outer_layout.addWidget(self.btn_save_beat_text, 0, Qt.AlignmentFlag.AlignRight)
        beat_layout.addWidget(detail_group)
        beat_layout.addStretch()

        splitter.addWidget(scene_box)
        splitter.addWidget(beat_box)
        splitter.setSizes([560, 640])
        layout.addWidget(splitter)

    def refresh(self) -> None:
        self._refreshing = True
        try:
            self.chapter_list.clear()
            self.episode_list.clear()

            if not self.app_state.project:
                self._update_readiness_status(None)
                self._refresh_structure_preview()
                return

            for chapter in self.app_state.project.source_chapters:
                item = QListWidgetItem(f"{chapter.chapter_number} | {chapter.title}")
                item.setData(ITEM_ROLE, chapter.chapter_id)
                self.chapter_list.addItem(item)
                if chapter.chapter_id in (self.app_state.selected_chapter_ids or []):
                    item.setSelected(True)

            for episode in self.app_state.project.review_episodes:
                item = QListWidgetItem(f"{episode.title}\n{episode.episode_id}")
                item.setData(ITEM_ROLE, episode.episode_id)
                self.episode_list.addItem(item)
                if episode.episode_id == self.app_state.selected_episode_id:
                    self.episode_list.setCurrentItem(item)

            if (
                self.app_state.project.review_episodes
                and self.app_state.selected_episode_id is None
            ):
                first_episode = self.app_state.project.review_episodes[0]
                self.app_state.selected_episode_id = first_episode.episode_id
                self.episode_list.setCurrentRow(0)

            self._update_readiness_status(self.app_state.project)
            self._refresh_structure_preview()
        finally:
            self._refreshing = False

    def _update_readiness_status(self, project) -> None:
        if not project:
            self.lbl_status_char.setText("- Characters: -")
            self.lbl_status_loc.setText("- Locations: -")
            self.lbl_status_style.setText("- Styles: -")
            self.lbl_status_warning.setText("")
            return

        chars = len(project.characters)
        locs = len(project.locations)
        styles = len(project.style_presets)

        self.lbl_status_char.setText(f"- Characters: {'available' if chars else 'missing'} ({chars})")
        self.lbl_status_char.setStyleSheet("color: green;" if chars else "color: red;")
        self.lbl_status_loc.setText(f"- Locations: {'available' if locs else 'missing'} ({locs})")
        self.lbl_status_loc.setStyleSheet("color: green;" if locs else "color: red;")
        self.lbl_status_style.setText(f"- Styles: {'available' if styles else 'missing'} ({styles})")
        self.lbl_status_style.setStyleSheet("color: green;" if styles else "color: red;")

        if chars == 0 or locs == 0 or styles == 0:
            self.lbl_status_warning.setText(
                "Bạn nên phân tích Bible / Style trước để kế hoạch tập và prompt ảnh nhất quán hơn."
            )
        else:
            self.lbl_status_warning.setText("")

    def _refresh_structure_preview(self) -> None:
        self.scene_tree.clear()
        self._clear_beat_detail()

        episode = self._current_episode()
        if episode is None or not self.app_state.project:
            return

        service = self.project_controller.project_service
        project = self.app_state.project

        selected_item: QTreeWidgetItem | None = None
        for scene in episode.scenes:
            mood = scene.mood or "no mood"
            loc_name = service.location_display_name(project, scene.location)
            char_names = [service.character_display_name(project, cid) for cid in scene.characters]
            char_names_str = ", ".join(char_names)
            
            scene_text = f"{scene.title} — {len(scene.beats)} beats | {mood} | {char_names_str}"
            if loc_name:
                scene_text += f" | {loc_name}"

            scene_item = QTreeWidgetItem([scene_text])
            
            tooltip = (
                f"Phân cảnh: {scene.title}\n"
                f"Tóm tắt: {scene.summary}\n"
                f"Số nhịp: {len(scene.beats)}\n"
                f"Cảm xúc: {mood}\n"
                f"Nhân vật: {char_names_str}\n"
                f"Địa điểm: {loc_name}"
            )
            scene_item.setToolTip(0, tooltip)
            
            scene_item.setData(0, ITEM_TYPE_ROLE, "scene")
            scene_item.setData(0, ITEM_ROLE, scene.scene_id)
            scene_item.setData(0, SCENE_ROLE, scene.scene_id)
            scene_item.setData(0, BEAT_ROLE, "")
            
            # Bold scene title
            font = scene_item.font(0)
            font.setBold(True)
            scene_item.setFont(0, font)

            self.scene_tree.addTopLevelItem(scene_item)
            scene_item.setFirstColumnSpanned(True)
            
            if scene.scene_id == self.app_state.selected_scene_id:
                selected_item = scene_item

            for beat in scene.ordered_beats():
                beat_item = QTreeWidgetItem([
                    f"Beat {beat.order_index}: {self._beat_preview_text(beat)}",
                    beat.story_function,
                    beat.emotion,
                    beat.shot_type
                ])
                beat_item.setData(0, ITEM_TYPE_ROLE, "beat")
                beat_item.setData(0, ITEM_ROLE, beat.beat_id)
                beat_item.setData(0, SCENE_ROLE, scene.scene_id)
                beat_item.setData(0, BEAT_ROLE, beat.beat_id)
                scene_item.addChild(beat_item)
                
                if beat.beat_id == self.app_state.selected_beat_id:
                    selected_item = beat_item

        if selected_item is not None:
            self.scene_tree.setCurrentItem(selected_item)
            # Expand parent if it's a beat, or expand self if it's a scene
            if selected_item.parent():
                selected_item.parent().setExpanded(True)
            else:
                selected_item.setExpanded(True)
        else:
            # Default: all collapsed
            self.scene_tree.collapseAll()

    def _beat_preview_text(self, beat: Beat) -> str:
        preview = beat.review_text or beat.action or beat.visual_description
        preview = re.sub(r"\s+", " ", preview).strip()
        if len(preview) > 80:
            preview = preview[:77].rstrip() + "..."
        return preview

    def _on_episode_select(self, current: QListWidgetItem | None, previous: object) -> None:
        if self._refreshing:
            return

        new_id = current.data(ITEM_ROLE) if current else None
        if new_id == self.app_state.selected_episode_id:
            # No change. Preserve selection.
            self._refresh_structure_preview()
            return

        self.app_state.selected_episode_id = new_id
        self.app_state.selected_scene_id = None
        self.app_state.selected_beat_id = None
        self._refresh_structure_preview()

    def _on_structure_item_select(self) -> None:
        current = self.scene_tree.currentItem()
        if not current:
            self.app_state.selected_scene_id = None
            self.app_state.selected_beat_id = None
            self._clear_beat_detail()
            return

        item_type = str(current.data(0, ITEM_TYPE_ROLE) or "")
        scene_id = str(current.data(0, SCENE_ROLE) or "")
        beat_id = str(current.data(0, BEAT_ROLE) or "")
        self.app_state.selected_scene_id = scene_id or None

        if item_type == "beat" and beat_id:
            self.app_state.selected_beat_id = beat_id
            self._load_beat_detail(self._current_beat())
            return

        self.app_state.selected_beat_id = None
        self._clear_beat_detail()

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        item_type = item.data(0, ITEM_TYPE_ROLE)
        if item_type == "scene":
            # Toggle expansion
            is_expanded = item.isExpanded()
            
            # Requirement: Preferred single-expanded scene
            # Collapse others
            root = self.scene_tree.invisibleRootItem()
            for i in range(root.childCount()):
                child = root.child(i)
                if child != item:
                    child.setExpanded(False)
            
            # Toggle self
            item.setExpanded(not is_expanded)

    def _on_chapter_selection_changed(self) -> None:
        chapter_ids = self._selected_chapter_ids()
        self.app_state.selected_chapter_ids = chapter_ids
        self.app_state.selected_chapter_id = chapter_ids[0] if chapter_ids else None

    def _on_delete_episode(self) -> None:
        if not self.app_state.project or not self.app_state.selected_episode_id:
            QMessageBox.warning(self, "Cảnh báo", "Hãy chọn tập cần xóa.")
            return

        episode_id = self.app_state.selected_episode_id
        episode_name = episode_id
        for episode in self.app_state.project.review_episodes:
            if episode.episode_id == episode_id:
                episode_name = episode.title
                break

        reply = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa tập '{episode_name}'?\n"
            "Tất cả phân cảnh và beat trong tập này sẽ bị xóa.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.app_state.project.review_episodes = [
            episode
            for episode in self.app_state.project.review_episodes
            if episode.episode_id != episode_id
        ]
        self.app_state.project.touch()
        self.app_state.selected_episode_id = None
        self.app_state.selected_scene_id = None
        self.app_state.selected_beat_id = None
        self.refresh_callback()
        self.refresh()

    def _on_prompt_plan(self) -> None:
        if not self.app_state.project:
            QMessageBox.warning(self, "Cảnh báo", "Hãy tạo hoặc mở dự án trước.")
            return

        step = self._current_step()
        chapter_ids = self._selected_chapter_ids()
        episode_id = self.app_state.selected_episode_id

        if step in {"plan-episode-with-review", "plan-episode"} and not chapter_ids:
            QMessageBox.warning(self, "Cảnh báo", "Hãy chọn ít nhất một chương.")
            return
        if step in {"generate-beats", "rewrite-review"} and not episode_id:
            QMessageBox.warning(self, "Cảnh báo", "Hãy chọn một tập truyện.")
            return

        try:
            prompt_text = self.manual_ai_controller.export_prompt(
                self.app_state.project,
                step,
                chapter_id=chapter_ids[0] if chapter_ids else None,
                chapter_ids=chapter_ids,
                episode_id=episode_id,
                episode_title=self.title_edit.text().strip(),
                tone=self._current_tone(),
                density=self._current_density(),
            )
            self.prompt_preview.setPlainText(prompt_text)
            self.apply_summary_label.setText("Đã tạo prompt. Hãy copy sang AI bên ngoài.")
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_copy_prompt(self) -> None:
        QApplication.clipboard().setText(self.prompt_preview.toPlainText())
        self.apply_summary_label.setText("Đã copy prompt.")

    def _on_import_plan(self) -> None:
        if not self.app_state.project:
            QMessageBox.warning(self, "Cảnh báo", "Hãy tạo hoặc mở dự án trước.")
            return

        raw_json = self.result_input.toPlainText().strip()
        if not raw_json:
            QMessageBox.warning(self, "Cảnh báo", "Hãy dán JSON kết quả trước.")
            return

        step = self._current_step()
        chapter_ids = self._selected_chapter_ids()
        if step in {"plan-episode-with-review", "plan-episode"} and not chapter_ids:
            QMessageBox.warning(self, "Cảnh báo", "Hãy chọn ít nhất một chương.")
            return

        try:
            result_data = self._parse_result_json(raw_json)
            summary = self.manual_ai_controller.import_result(
                self.app_state.project,
                step,
                result_data,
                chapter_id=chapter_ids[0] if chapter_ids else None,
                chapter_ids=chapter_ids,
                episode_id=self.app_state.selected_episode_id,
                tone=self._current_tone(),
                density=self._current_density(),
            )
            self._select_imported_episode(result_data)
            self.apply_summary_label.setText(summary)
            self.refresh()
            self.refresh_callback()
            QMessageBox.information(self, "Thành công", summary)
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_save_beat_text_changes(self) -> None:
        beat = self._current_beat()
        if not beat or not self.app_state.project:
            QMessageBox.warning(self, "Cảnh báo", "Hãy chọn một beat.")
            return

        service = self.project_controller.project_service
        project = self.app_state.project
        
        beat.story_function = self.beat_story_function_edit.text().strip()
        try:
            beat.order_index = int(self.beat_order_index_edit.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Cáº£nh bÃ¡o", "Order Index pháº£i lÃ  sá»‘ nguyÃªn.")
            return
        beat.action = self.beat_action_edit.text().strip()
        beat.emotion = self.beat_emotion_edit.text().strip()
        beat.visual_description = self.beat_visual_description_edit.text().strip()
        beat.camera = self.beat_camera_edit.text().strip()
        beat.shot_type = self.beat_shot_type_edit.text().strip()
        beat.timeOfDay = self.beat_time_of_day_edit.text().strip()
        beat.lighting = self.beat_lighting_edit.text().strip()
        beat.atmosphere = self.beat_atmosphere_edit.text().strip()
        beat.location_cues = self.beat_location_cues_edit.text().strip()
        beat.asmr_visuals = self.beat_asmr_visuals_edit.text().strip()
        beat.composition = self.beat_composition_edit.text().strip()
        beat.posture = self.beat_posture_edit.text().strip()
        beat.expression = self.beat_expression_edit.text().strip()
        beat.body_language = self.beat_body_language_edit.text().strip()
        beat.review_text = self.beat_review_text_edit.toPlainText().strip()
        
        # Resolve names back to IDs
        char_names = self._split_csv(self.beat_characters_edit.text())
        beat.characters = [service.resolve_character_id(project, name) for name in char_names]
        beat.character_variants = self._parse_character_mapping_text(
            self.beat_character_variants_edit.text(),
            beat.characters,
            mapping_kind="variant",
        )
        beat.character_outfits = self._parse_character_mapping_text(
            self.beat_character_outfits_edit.text(),
            beat.characters,
            mapping_kind="outfit",
        )
        
        loc_name = self.beat_location_edit.text().strip()
        beat.location = service.resolve_location_id(project, loc_name)
        
        # Resolve tags back to IDs
        tags_str = self.beat_continuity_tags_edit.text().strip()
        beat.continuity_tags = self.tag_service.resolve_display_names(project, tags_str)
        beat.props = self._split_csv(self.beat_props_edit.text())
        beat.wardrobe_notes = self.beat_wardrobe_notes_edit.text().strip()
        beat.character_state = self.beat_character_state_edit.text().strip()
        beat.location_state = self.beat_location_state_edit.text().strip()
        beat.transition_note = self.beat_transition_note_edit.text().strip()
        
        self.app_state.project.touch()
        self._refresh_structure_preview()
        self.apply_summary_label.setText("Đã lưu thay đổi text/story cho beat.")
        self.refresh_callback()

    def _load_beat_detail(self, beat: Beat | None) -> None:
        self._clear_beat_detail()
        if beat is None:
            return
        service = self.project_controller.project_service
        project = self.app_state.project
        
        self.beat_id_edit.setText(beat.beat_id)
        self.beat_scene_id_edit.setText(beat.scene_id)
        self.beat_order_index_edit.setText(str(beat.order_index))
        self.beat_story_function_edit.setText(beat.story_function)
        self.beat_action_edit.setText(beat.action)
        self.beat_emotion_edit.setText(beat.emotion)
        self.beat_visual_description_edit.setText(beat.visual_description)
        self.beat_camera_edit.setText(beat.camera)
        self.beat_shot_type_edit.setText(beat.shot_type)
        self.beat_time_of_day_edit.setText(beat.timeOfDay)
        self.beat_lighting_edit.setText(beat.lighting)
        self.beat_atmosphere_edit.setText(beat.atmosphere)
        self.beat_location_cues_edit.setText(beat.location_cues)
        self.beat_asmr_visuals_edit.setText(beat.asmr_visuals)
        self.beat_composition_edit.setText(beat.composition)
        self.beat_posture_edit.setText(beat.posture)
        self.beat_expression_edit.setText(beat.expression)
        self.beat_body_language_edit.setText(beat.body_language)
        self.beat_review_text_edit.setPlainText(beat.review_text)
        
        # Show names instead of IDs
        char_names = [service.character_display_name(project, cid) for cid in beat.characters]
        self.beat_characters_edit.setText(", ".join(char_names))
        self.beat_character_variants_edit.setText(
            self._format_character_mapping(
                beat.characters,
                beat.character_variants,
                mapping_kind="variant",
            )
        )
        self.beat_character_outfits_edit.setText(
            self._format_character_mapping(
                beat.characters,
                beat.character_outfits,
                mapping_kind="outfit",
            )
        )
        
        loc_name = service.location_display_name(project, beat.location)
        self.beat_location_edit.setText(loc_name)
        
        # Show tag names instead of IDs
        tag_names = self.tag_service.to_display_names(project, beat.continuity_tags)
        self.beat_continuity_tags_edit.setText(", ".join(tag_names))
        self.beat_props_edit.setText(", ".join(beat.props))
        self.beat_wardrobe_notes_edit.setText(beat.wardrobe_notes)
        self.beat_character_state_edit.setText(beat.character_state)
        self.beat_location_state_edit.setText(beat.location_state)
        self.beat_transition_note_edit.setText(beat.transition_note)

    def _clear_beat_detail(self) -> None:
        self.beat_id_edit.clear()
        self.beat_scene_id_edit.clear()
        self.beat_order_index_edit.clear()
        self.beat_story_function_edit.clear()
        self.beat_action_edit.clear()
        self.beat_emotion_edit.clear()
        self.beat_visual_description_edit.clear()
        self.beat_camera_edit.clear()
        self.beat_shot_type_edit.clear()
        self.beat_time_of_day_edit.clear()
        self.beat_lighting_edit.clear()
        self.beat_atmosphere_edit.clear()
        self.beat_location_cues_edit.clear()
        self.beat_asmr_visuals_edit.clear()
        self.beat_composition_edit.clear()
        self.beat_posture_edit.clear()
        self.beat_expression_edit.clear()
        self.beat_body_language_edit.clear()
        self.beat_review_text_edit.clear()
        self.beat_characters_edit.clear()
        self.beat_character_variants_edit.clear()
        self.beat_character_outfits_edit.clear()
        self.beat_location_edit.clear()
        self.beat_continuity_tags_edit.clear()
        self.beat_props_edit.clear()
        self.beat_wardrobe_notes_edit.clear()
        self.beat_character_state_edit.clear()
        self.beat_location_state_edit.clear()
        self.beat_transition_note_edit.clear()

    def _select_imported_episode(self, result_data: dict) -> None:
        episode_data = result_data.get("episode", {}) if isinstance(result_data, dict) else {}
        episode_id = episode_data.get("episode_id") if isinstance(episode_data, dict) else None
        if episode_id:
            self.app_state.selected_episode_id = str(episode_id)
            return
        if self.app_state.project and self.app_state.project.review_episodes:
            self.app_state.selected_episode_id = self.app_state.project.review_episodes[-1].episode_id

    def _current_episode(self) -> ReviewEpisode | None:
        if not self.app_state.project or not self.app_state.selected_episode_id:
            return None
        for episode in self.app_state.project.review_episodes:
            if episode.episode_id == self.app_state.selected_episode_id:
                return episode
        return None

    def _current_scene(self) -> Scene | None:
        episode = self._current_episode()
        if not episode or not self.app_state.selected_scene_id:
            return None
        for scene in episode.scenes:
            if scene.scene_id == self.app_state.selected_scene_id:
                return scene
        return None

    def _current_beat(self) -> Beat | None:
        scene = self._current_scene()
        if not scene or not self.app_state.selected_beat_id:
            return None
        for beat in scene.beats:
            if beat.beat_id == self.app_state.selected_beat_id:
                return beat
        return None

    def _selected_chapter_ids(self) -> list[str]:
        selected_items = self.chapter_list.selectedItems()
        return [str(item.data(ITEM_ROLE)) for item in selected_items]

    def _selected_chapter_id(self) -> str | None:
        chapter_ids = self._selected_chapter_ids()
        return chapter_ids[0] if chapter_ids else None

    def _current_tone(self) -> str:
        return self._tone_map.get(self.tone_combo.currentText(), "mysterious")

    def _current_density(self) -> str:
        return self._density_map.get(self.density_combo.currentText(), "full")

    def _current_step(self) -> str:
        return str(self.manual_task_combo.currentData() or "plan-episode-with-review")

    def _format_character_mapping(
        self,
        character_ids: list[str],
        mapping: dict[str, str],
        *,
        mapping_kind: str,
    ) -> str:
        if not self.app_state.project:
            return ""
        project = self.app_state.project
        parts: list[str] = []
        for character_id in character_ids:
            target_id = mapping.get(character_id, "")
            if not target_id:
                continue
            character = next(
                (item for item in project.characters if item.character_id == character_id),
                None,
            )
            character_name = character.name if character else character_id
            target_name = target_id
            if character:
                if mapping_kind == "variant":
                    variant = character.find_variant(target_id)
                    if variant and variant.display_name:
                        target_name = variant.display_name
                else:
                    outfit = character.find_outfit(target_id)
                    if outfit and outfit.display_name:
                        target_name = outfit.display_name
            parts.append(f"{character_name} -> {target_name}")
        return "; ".join(parts)

    def _parse_character_mapping_text(
        self,
        text: str,
        character_ids: list[str],
        *,
        mapping_kind: str,
    ) -> dict[str, str]:
        if not self.app_state.project:
            return {}
        project = self.app_state.project
        mapping: dict[str, str] = {}
        entries = [item.strip() for item in re.split(r"[;\n]+", text.strip()) if item.strip()]
        for entry in entries:
            if "->" in entry:
                left, right = entry.split("->", 1)
            elif ":" in entry:
                left, right = entry.split(":", 1)
            else:
                continue
            character_id = self.project_controller.project_service.resolve_character_id(
                project,
                left.strip(),
            )
            if character_id not in character_ids:
                if len(character_ids) == 1:
                    character_id = character_ids[0]
                else:
                    continue
            target_id = self._resolve_variant_or_outfit_id(
                character_id,
                right.strip(),
                mapping_kind=mapping_kind,
            )
            if target_id:
                mapping[character_id] = target_id

        if not mapping and len(character_ids) == 1 and text.strip():
            character_id = character_ids[0]
            target_id = self._resolve_variant_or_outfit_id(
                character_id,
                text.strip(),
                mapping_kind=mapping_kind,
            )
            if target_id:
                mapping[character_id] = target_id
        return mapping

    def _resolve_variant_or_outfit_id(
        self,
        character_id: str,
        token: str,
        *,
        mapping_kind: str,
    ) -> str:
        if not self.app_state.project:
            return token
        if "->" in token:
            token = token.split("->", 1)[1].strip()
        if ":" in token and mapping_kind in {"variant", "outfit"}:
            token = token.split(":", 1)[1].strip()
        character = next(
            (item for item in self.app_state.project.characters if item.character_id == character_id),
            None,
        )
        if not character:
            return token
        token_key = token.lower()
        if mapping_kind == "variant":
            for variant in character.variants:
                if variant.variant_id.lower() == token_key:
                    return variant.variant_id
                if (variant.display_name or "").strip().lower() == token_key:
                    return variant.variant_id
        else:
            for outfit in character.outfits:
                if outfit.outfit_id.lower() == token_key:
                    return outfit.outfit_id
                if (outfit.display_name or "").strip().lower() == token_key:
                    return outfit.outfit_id
        return token

    def _parse_result_json(self, text: str) -> dict:
        cleaned = self._strip_code_block(text)
        data = json.loads(cleaned)
        if not isinstance(data, dict):
            raise ValueError("Kết quả phải là JSON object.")
        return data

    def _strip_code_block(self, text: str) -> str:
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text

    def _split_csv(self, value: str) -> list[str]:
        return [part.strip() for part in value.split(",") if part.strip()]
