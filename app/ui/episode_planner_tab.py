"""Episode planner tab."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
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
    QSplitter,
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

        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self.setup_group = QGroupBox("Episode Setup")
        setup_layout = QGridLayout(self.setup_group)
        self._build_setup_section(setup_layout)
        main_layout.addWidget(self.setup_group)

        self.prompt_workflow_group = QGroupBox("Manual AI Prompt Workflow")
        workflow_layout = QVBoxLayout(self.prompt_workflow_group)
        self._build_prompt_workflow_section(workflow_layout)
        main_layout.addWidget(self.prompt_workflow_group, 2)

        self.structure_preview_group = QGroupBox("Episode Structure Preview")
        preview_layout = QVBoxLayout(self.structure_preview_group)
        self._build_structure_preview_section(preview_layout)
        main_layout.addWidget(self.structure_preview_group, 3)

        self.btn_delete_episode.clicked.connect(self._on_delete_episode)
        self.btn_prompt_plan.clicked.connect(self._on_prompt_plan)
        self.btn_copy_prompt.clicked.connect(self._on_copy_prompt)
        self.btn_import_plan.clicked.connect(self._on_import_plan)
        self.btn_save_beat_text.clicked.connect(self._on_save_beat_text_changes)
        self.chapter_list.itemSelectionChanged.connect(self._on_chapter_selection_changed)
        self.episode_list.currentItemChanged.connect(self._on_episode_select)
        self.scene_list.currentItemChanged.connect(self._on_structure_item_select)

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
        self.chapter_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        chapter_layout.addWidget(self.chapter_list)
        layout.addWidget(chapter_box, 0, 1)

        episode_box = QGroupBox("Episode selector")
        episode_layout = QVBoxLayout(episode_box)
        self.episode_list = QListWidget()
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
        prompt_layout.addWidget(QLabel("Prompt preview"))
        self.prompt_preview = QPlainTextEdit()
        self.prompt_preview.setReadOnly(True)
        self.prompt_preview.setPlaceholderText("Prompt sẽ hiện ở đây để copy sang AI bên ngoài.")
        self.prompt_preview.setMinimumHeight(180)
        prompt_layout.addWidget(self.prompt_preview)

        result_box = QWidget()
        result_layout = QVBoxLayout(result_box)
        result_layout.addWidget(QLabel("AI JSON result input"))
        self.result_input = QPlainTextEdit()
        self.result_input.setPlaceholderText("Dán JSON kết quả AI vào đây.")
        self.result_input.setMinimumHeight(180)
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
        self.scene_list = QListWidget()
        self.scene_list.setMinimumWidth(460)
        scene_layout.addWidget(self.scene_list)

        beat_box = QWidget()
        beat_layout = QVBoxLayout(beat_box)
        detail_group = QGroupBox("Selected beat text/story fields")
        detail_layout = QGridLayout(detail_group)
        self.beat_action_edit = QLineEdit()
        self.beat_emotion_edit = QLineEdit()
        self.beat_visual_description_edit = QLineEdit()
        self.beat_shot_type_edit = QLineEdit()
        self.beat_characters_edit = QLineEdit()
        self.beat_location_edit = QLineEdit()
        self.beat_continuity_tags_edit = QLineEdit()
        self.beat_review_text_edit = QPlainTextEdit()
        self.beat_review_text_edit.setMinimumHeight(90)
        self.btn_save_beat_text = QPushButton("Save Beat Text Changes")

        detail_layout.addWidget(QLabel("Action"), 0, 0)
        detail_layout.addWidget(self.beat_action_edit, 0, 1)
        detail_layout.addWidget(QLabel("Emotion"), 0, 2)
        detail_layout.addWidget(self.beat_emotion_edit, 0, 3)
        detail_layout.addWidget(QLabel("Visual Description"), 1, 0)
        detail_layout.addWidget(self.beat_visual_description_edit, 1, 1)
        detail_layout.addWidget(QLabel("Shot Type"), 1, 2)
        detail_layout.addWidget(self.beat_shot_type_edit, 1, 3)
        detail_layout.addWidget(QLabel("Characters"), 2, 0)
        detail_layout.addWidget(self.beat_characters_edit, 2, 1)
        detail_layout.addWidget(QLabel("Location"), 2, 2)
        detail_layout.addWidget(self.beat_location_edit, 2, 3)
        detail_layout.addWidget(QLabel("Continuity Tags"), 3, 0)
        detail_layout.addWidget(self.beat_continuity_tags_edit, 3, 1, 1, 3)
        detail_layout.addWidget(QLabel("Review Text"), 4, 0)
        detail_layout.addWidget(self.beat_review_text_edit, 4, 1, 1, 3)
        detail_layout.addWidget(self.btn_save_beat_text, 5, 3)
        beat_layout.addWidget(detail_group)
        beat_layout.addStretch()

        splitter.addWidget(scene_box)
        splitter.addWidget(beat_box)
        splitter.setSizes([560, 640])
        layout.addWidget(splitter)

    def refresh(self) -> None:
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
        self.scene_list.clear()
        self._clear_beat_detail()

        episode = self._current_episode()
        if episode is None:
            return

        selected_item: QListWidgetItem | None = None
        for scene in episode.scenes:
            chars = ", ".join(scene.characters[:3])
            detail_bits = [f"{len(scene.beats)} beats"]
            if scene.mood:
                detail_bits.append(scene.mood)
            if chars:
                detail_bits.append(chars)
            item = QListWidgetItem(f"{scene.title}\n{' | '.join(detail_bits)}")
            item.setData(ITEM_TYPE_ROLE, "scene")
            item.setData(ITEM_ROLE, scene.scene_id)
            item.setData(SCENE_ROLE, scene.scene_id)
            item.setData(BEAT_ROLE, "")
            self.scene_list.addItem(item)
            if scene.scene_id == self.app_state.selected_scene_id:
                selected_item = item

            for beat in scene.ordered_beats():
                beat_item = QListWidgetItem(self._beat_list_text(beat))
                beat_item.setData(ITEM_TYPE_ROLE, "beat")
                beat_item.setData(ITEM_ROLE, beat.beat_id)
                beat_item.setData(SCENE_ROLE, scene.scene_id)
                beat_item.setData(BEAT_ROLE, beat.beat_id)
                self.scene_list.addItem(beat_item)
                if beat.beat_id == self.app_state.selected_beat_id:
                    selected_item = beat_item

        if selected_item is not None:
            self.scene_list.setCurrentItem(selected_item)
        elif self.scene_list.count() > 0 and self.scene_list.currentRow() < 0:
            self.scene_list.setCurrentRow(0)

    def _beat_list_text(self, beat: Beat) -> str:
        preview = beat.review_text or beat.action or beat.visual_description
        preview = re.sub(r"\s+", " ", preview).strip()
        if len(preview) > 120:
            preview = preview[:117].rstrip() + "..."
        meta = " | ".join(
            part
            for part in [
                f"#{beat.order_index}",
                beat.story_function,
                beat.emotion,
                beat.shot_type,
            ]
            if part
        )
        return f"   Beat {beat.order_index}: {preview}\n   {meta}"

    def _on_episode_select(self, current: QListWidgetItem | None, previous: object) -> None:
        if current:
            self.app_state.selected_episode_id = current.data(ITEM_ROLE)
        else:
            self.app_state.selected_episode_id = None
        self.app_state.selected_scene_id = None
        self.app_state.selected_beat_id = None
        self._refresh_structure_preview()

    def _on_structure_item_select(
        self,
        current: QListWidgetItem | None,
        previous: object,
    ) -> None:
        if not current:
            self.app_state.selected_scene_id = None
            self.app_state.selected_beat_id = None
            self._clear_beat_detail()
            return

        item_type = str(current.data(ITEM_TYPE_ROLE) or "")
        scene_id = str(current.data(SCENE_ROLE) or "")
        beat_id = str(current.data(BEAT_ROLE) or "")
        self.app_state.selected_scene_id = scene_id or None

        if item_type == "beat" and beat_id:
            self.app_state.selected_beat_id = beat_id
            self._load_beat_detail(self._current_beat())
            return

        self.app_state.selected_beat_id = None
        self._clear_beat_detail()

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

        beat.action = self.beat_action_edit.text().strip()
        beat.emotion = self.beat_emotion_edit.text().strip()
        beat.visual_description = self.beat_visual_description_edit.text().strip()
        beat.shot_type = self.beat_shot_type_edit.text().strip()
        beat.review_text = self.beat_review_text_edit.toPlainText().strip()
        beat.characters = self._split_csv(self.beat_characters_edit.text())
        beat.location = self.beat_location_edit.text().strip()
        beat.continuity_tags = self._split_csv(self.beat_continuity_tags_edit.text())
        self.app_state.project.touch()
        self._refresh_structure_preview()
        self.apply_summary_label.setText("Đã lưu thay đổi text/story cho beat.")
        self.refresh_callback()

    def _load_beat_detail(self, beat: Beat | None) -> None:
        self._clear_beat_detail()
        if beat is None:
            return
        self.beat_action_edit.setText(beat.action)
        self.beat_emotion_edit.setText(beat.emotion)
        self.beat_visual_description_edit.setText(beat.visual_description)
        self.beat_shot_type_edit.setText(beat.shot_type)
        self.beat_review_text_edit.setPlainText(beat.review_text)
        self.beat_characters_edit.setText(", ".join(beat.characters))
        self.beat_location_edit.setText(beat.location)
        self.beat_continuity_tags_edit.setText(", ".join(beat.continuity_tags))

    def _clear_beat_detail(self) -> None:
        self.beat_action_edit.clear()
        self.beat_emotion_edit.clear()
        self.beat_visual_description_edit.clear()
        self.beat_shot_type_edit.clear()
        self.beat_review_text_edit.clear()
        self.beat_characters_edit.clear()
        self.beat_location_edit.clear()
        self.beat_continuity_tags_edit.clear()

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
