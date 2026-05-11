"""Tab for Character Bible, Location Bible, and Style Presets."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from app.controllers.bible_controller import BibleController
    from app.ui.app_state import AppState

ITEM_ROLE = Qt.ItemDataRole.UserRole


class BibleStyleTab(QWidget):
    def __init__(
        self,
        app_state: AppState,
        bible_controller: BibleController,
        refresh_callback: callable,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.bible_controller = bible_controller
        self.refresh_callback = refresh_callback
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        self.tabs.addTab(self._build_character_bible(), "Nhân vật")
        self.tabs.addTab(self._build_location_bible(), "Địa điểm")
        self.tabs.addTab(self._build_style_presets(), "Style Presets")
        self.tabs.addTab(self._build_ai_analysis(), "Phân tích AI")

        layout.addWidget(self.tabs)

    def _add_row(self, layout: QGridLayout, row: int, label_text: str, widget: QWidget) -> int:
        layout.addWidget(QLabel(label_text), row, 0)
        layout.addWidget(widget, row, 1)
        return row + 1

    def _build_character_bible(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)

        # Left: List
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        self.char_list = QListWidget()
        left_layout.addWidget(self.char_list)

        char_btn_layout = QHBoxLayout()
        self.btn_add_char = QPushButton("Thêm")
        self.btn_del_char = QPushButton("Xóa")
        char_btn_layout.addWidget(self.btn_add_char)
        char_btn_layout.addWidget(self.btn_del_char)
        left_layout.addLayout(char_btn_layout)
        layout.addWidget(left_widget, 1)

        # Right: Scrollable Form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_container = QWidget()
        form_main_layout = QVBoxLayout(form_container)

        # 1. Core Identity Section
        core_group = QGroupBox("Core Identity")
        core_layout = QGridLayout(core_group)
        self.char_id = QLineEdit(); self.char_id.setReadOnly(True)
        self.char_name = QLineEdit()
        self.char_aliases = QLineEdit()
        self.char_role = QLineEdit()
        self.char_gender = QLineEdit()
        self.char_age = QLineEdit()
        self.char_personality = QLineEdit()
        self.char_appearance = QPlainTextEdit()
        self.char_appearance.setMaximumHeight(60)
        self.char_face = QLineEdit()
        self.char_hair = QLineEdit()
        self.char_eyes = QLineEdit()
        self.char_body = QLineEdit()
        self.char_voice = QLineEdit()
        self.char_rel = QLineEdit()
        self.char_tags = QLineEdit()

        r = 0
        r = self._add_row(core_layout, r, "ID:", self.char_id)
        r = self._add_row(core_layout, r, "Tên:", self.char_name)
        r = self._add_row(core_layout, r, "Bí danh:", self.char_aliases)
        r = self._add_row(core_layout, r, "Vai trò:", self.char_role)
        r = self._add_row(core_layout, r, "Giới tính:", self.char_gender)
        r = self._add_row(core_layout, r, "Tuổi:", self.char_age)
        r = self._add_row(core_layout, r, "Tính cách:", self.char_personality)
        r = self._add_row(core_layout, r, "Ngoại hình:", self.char_appearance)
        r = self._add_row(core_layout, r, "Khuôn mặt:", self.char_face)
        r = self._add_row(core_layout, r, "Tóc:", self.char_hair)
        r = self._add_row(core_layout, r, "Mắt:", self.char_eyes)
        r = self._add_row(core_layout, r, "Dáng người:", self.char_body)
        r = self._add_row(core_layout, r, "Giọng nói:", self.char_voice)
        r = self._add_row(core_layout, r, "Quan hệ:", self.char_rel)
        r = self._add_row(core_layout, r, "Tags:", self.char_tags)
        form_main_layout.addWidget(core_group)

        # 2. Beat Prompt Data Section
        beat_group = QGroupBox("Beat Prompt Data")
        beat_layout = QGridLayout(beat_group)
        self.char_prompt_base = QPlainTextEdit(); self.char_prompt_base.setMaximumHeight(60)
        self.char_outfit = QLineEdit()
        self.char_outfit_variants = QLineEdit()
        self.char_neg_terms = QLineEdit()
        self.char_sig_features = QLineEdit()
        self.char_must_keep = QLineEdit()
        self.char_forbidden = QLineEdit()
        self.char_ref_note = QLineEdit()

        r = 0
        r = self._add_row(beat_layout, r, "Prompt Base:", self.char_prompt_base)
        r = self._add_row(beat_layout, r, "Trang phục mặc định:", self.char_outfit)
        r = self._add_row(beat_layout, r, "Biến thể đồ:", self.char_outfit_variants)
        r = self._add_row(beat_layout, r, "Negative:", self.char_neg_terms)
        r = self._add_row(beat_layout, r, "Signature Features:", self.char_sig_features)
        r = self._add_row(beat_layout, r, "Must Keep:", self.char_must_keep)
        r = self._add_row(beat_layout, r, "Forbidden:", self.char_forbidden)
        r = self._add_row(beat_layout, r, "Reference Note:", self.char_ref_note)
        form_main_layout.addWidget(beat_group)

        # 3. Reference Sheet Data Section
        ref_group = QGroupBox("Reference Sheet Data")
        ref_layout = QGridLayout(ref_group)
        self.char_ref_views = QLineEdit()
        self.char_ref_expr = QPlainTextEdit(); self.char_ref_expr.setMaximumHeight(60)
        self.char_ref_micro = QLineEdit()
        self.char_ref_angles = QLineEdit()
        self.char_ref_poses = QLineEdit()
        self.char_ref_hands = QLineEdit()
        self.char_ref_wardrobe = QPlainTextEdit(); self.char_ref_wardrobe.setMaximumHeight(60)
        self.char_ref_props = QLineEdit()
        self.char_ref_palette = QLineEdit()
        self.char_ref_layout = QLineEdit()
        self.char_ref_notes = QPlainTextEdit(); self.char_ref_notes.setMaximumHeight(60)

        r = 0
        r = self._add_row(ref_layout, r, "Required Views:", self.char_ref_views)
        r = self._add_row(ref_layout, r, "Expression Set:", self.char_ref_expr)
        r = self._add_row(ref_layout, r, "Micro Expressions:", self.char_ref_micro)
        r = self._add_row(ref_layout, r, "Head Angles:", self.char_ref_angles)
        r = self._add_row(ref_layout, r, "Pose Set:", self.char_ref_poses)
        r = self._add_row(ref_layout, r, "Hand Gestures:", self.char_ref_hands)
        r = self._add_row(ref_layout, r, "Wardrobe Details:", self.char_ref_wardrobe)
        r = self._add_row(ref_layout, r, "Prop Details:", self.char_ref_props)
        r = self._add_row(ref_layout, r, "Color Palette:", self.char_ref_palette)
        r = self._add_row(ref_layout, r, "Layout Style:", self.char_ref_layout)
        r = self._add_row(ref_layout, r, "General Notes:", self.char_ref_notes)
        form_main_layout.addWidget(ref_group)

        self.btn_save_char = QPushButton("Lưu nhân vật")
        self.btn_build_ref_prompt = QPushButton("Copy Prompt Ảnh Tham Chiếu")
        self.btn_build_ref_prompt.setObjectName("secondary-button")
        form_main_layout.addWidget(self.btn_save_char)
        form_main_layout.addWidget(self.btn_build_ref_prompt)

        scroll.setWidget(form_container)
        layout.addWidget(scroll, 2)

        self.char_list.currentItemChanged.connect(self._on_char_select)
        self.btn_add_char.clicked.connect(self._on_add_char)
        self.btn_del_char.clicked.connect(self._on_del_char)
        self.btn_save_char.clicked.connect(self._on_save_char)
        self.btn_build_ref_prompt.clicked.connect(self._on_build_ref_prompt)

        return widget

        return widget

    def _build_location_bible(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        self.loc_list = QListWidget()
        left_layout.addWidget(self.loc_list)

        loc_btn_layout = QHBoxLayout()
        self.btn_add_loc = QPushButton("Thêm")
        self.btn_del_loc = QPushButton("Xóa")
        loc_btn_layout.addWidget(self.btn_add_loc)
        loc_btn_layout.addWidget(self.btn_del_loc)
        left_layout.addLayout(loc_btn_layout)
        layout.addWidget(left_widget, 1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_container = QWidget()
        form_layout = QGridLayout(form_container)

        self.loc_id = QLineEdit()
        self.loc_id.setReadOnly(True)
        self.loc_name = QLineEdit()
        self.loc_aliases = QLineEdit()
        self.loc_type = QLineEdit()
        self.loc_desc = QPlainTextEdit()
        self.loc_desc.setMaximumHeight(60)
        self.loc_mood = QLineEdit()
        self.loc_time = QLineEdit()
        self.loc_lighting = QLineEdit()
        self.loc_palette = QLineEdit()
        self.loc_arch = QLineEdit()
        self.loc_props = QLineEdit()
        self.loc_prompt_base = QPlainTextEdit()
        self.loc_prompt_base.setMaximumHeight(60)
        self.loc_neg_terms = QLineEdit()
        self.loc_tags = QLineEdit()

        r = 0
        r = self._add_row(form_layout, r, "ID:", self.loc_id)
        r = self._add_row(form_layout, r, "Tên:", self.loc_name)
        r = self._add_row(form_layout, r, "Bí danh:", self.loc_aliases)
        r = self._add_row(form_layout, r, "Loại:", self.loc_type)
        r = self._add_row(form_layout, r, "Mô tả:", self.loc_desc)
        r = self._add_row(form_layout, r, "Tâm trạng:", self.loc_mood)
        r = self._add_row(form_layout, r, "Thời gian:", self.loc_time)
        r = self._add_row(form_layout, r, "Ánh sáng:", self.loc_lighting)
        r = self._add_row(form_layout, r, "Bảng màu:", self.loc_palette)
        r = self._add_row(form_layout, r, "Kiến trúc:", self.loc_arch)
        r = self._add_row(form_layout, r, "Đạo cụ:", self.loc_props)
        r = self._add_row(form_layout, r, "Prompt Base:", self.loc_prompt_base)
        r = self._add_row(form_layout, r, "Negative:", self.loc_neg_terms)
        r = self._add_row(form_layout, r, "Tags:", self.loc_tags)

        self.btn_save_loc = QPushButton("Lưu địa điểm")
        form_layout.addWidget(self.btn_save_loc, r, 0, 1, 2)

        scroll.setWidget(form_container)
        layout.addWidget(scroll, 2)

        self.loc_list.currentItemChanged.connect(self._on_loc_select)
        self.btn_add_loc.clicked.connect(self._on_add_loc)
        self.btn_del_loc.clicked.connect(self._on_del_loc)
        self.btn_save_loc.clicked.connect(self._on_save_loc)

        return widget

    def _build_style_presets(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        self.style_list = QListWidget()
        left_layout.addWidget(self.style_list)

        style_btn_layout = QHBoxLayout()
        self.btn_add_style = QPushButton("Thêm")
        self.btn_del_style = QPushButton("Xóa")
        style_btn_layout.addWidget(self.btn_add_style)
        style_btn_layout.addWidget(self.btn_del_style)
        left_layout.addLayout(style_btn_layout)
        layout.addWidget(left_widget, 1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_container = QWidget()
        form_layout = QGridLayout(form_container)

        self.style_id = QLineEdit()
        self.style_id.setReadOnly(True)
        self.style_name = QLineEdit()
        self.style_desc = QPlainTextEdit()
        self.style_desc.setMaximumHeight(40)
        self.style_genre = QLineEdit()
        self.style_pos = QPlainTextEdit()
        self.style_pos.setMaximumHeight(60)
        self.style_neg = QPlainTextEdit()
        self.style_neg.setMaximumHeight(60)
        self.style_line = QLineEdit()
        self.style_palette = QLineEdit()
        self.style_lighting = QLineEdit()
        self.style_rendering = QLineEdit()
        self.style_char_rules = QLineEdit()
        self.style_bg_detail = QLineEdit()
        self.style_camera = QLineEdit()
        self.style_mood_keys = QLineEdit()
        self.style_forbidden = QLineEdit()

        r = 0
        r = self._add_row(form_layout, r, "ID:", self.style_id)
        r = self._add_row(form_layout, r, "Tên:", self.style_name)
        r = self._add_row(form_layout, r, "Mô tả:", self.style_desc)
        r = self._add_row(form_layout, r, "Thể loại:", self.style_genre)
        r = self._add_row(form_layout, r, "Positive:", self.style_pos)
        r = self._add_row(form_layout, r, "Negative:", self.style_neg)
        r = self._add_row(form_layout, r, "Line Style:", self.style_line)
        r = self._add_row(form_layout, r, "Palette:", self.style_palette)
        r = self._add_row(form_layout, r, "Lighting:", self.style_lighting)
        r = self._add_row(form_layout, r, "Rendering:", self.style_rendering)
        r = self._add_row(form_layout, r, "Char Rules:", self.style_char_rules)
        r = self._add_row(form_layout, r, "BG Detail:", self.style_bg_detail)
        r = self._add_row(form_layout, r, "Camera:", self.style_camera)
        r = self._add_row(form_layout, r, "Mood Keys:", self.style_mood_keys)
        r = self._add_row(form_layout, r, "Forbidden:", self.style_forbidden)

        self.btn_save_style = QPushButton("Lưu Style")
        self.btn_set_default_style = QPushButton("Đặt làm mặc định")
        self.btn_gen_default_styles = QPushButton("Tạo các Style mặc định")

        form_layout.addWidget(self.btn_save_style, r, 0, 1, 2)
        r += 1
        form_layout.addWidget(self.btn_set_default_style, r, 0, 1, 2)
        r += 1
        form_layout.addWidget(self.btn_gen_default_styles, r, 0, 1, 2)
        r += 1

        scroll.setWidget(form_container)
        layout.addWidget(scroll, 2)

        self.style_list.currentItemChanged.connect(self._on_style_select)
        self.btn_add_style.clicked.connect(self._on_add_style)
        self.btn_del_style.clicked.connect(self._on_del_style)
        self.btn_save_style.clicked.connect(self._on_save_style)
        self.btn_set_default_style.clicked.connect(self._on_set_default_style)
        self.btn_gen_default_styles.clicked.connect(self._on_gen_default_styles)

        return widget

    def _build_ai_analysis(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        warning_label = QLabel("⚠️ Phân tích Bible / Style trước khi tạo Kế hoạch tập.")
        warning_label.setStyleSheet("color: #ffaa00; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(warning_label)

        # 1. Source Selector
        source_group = QGroupBox("1. Chọn chương nguồn để phân tích")
        source_layout = QVBoxLayout(source_group)
        self.ai_source_list = QListWidget()
        self.ai_source_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.ai_source_list.setMaximumHeight(150)
        source_layout.addWidget(self.ai_source_list)
        
        hint_layout = QHBoxLayout()
        hint_layout.addWidget(QLabel("Style Hint (tùy chọn):"))
        self.ai_style_hint = QLineEdit()
        self.ai_style_hint.setPlaceholderText("Ví dụ: dark fantasy, webtoon style...")
        hint_layout.addWidget(self.ai_style_hint)
        source_layout.addLayout(hint_layout)
        
        self.btn_gen_ai_prompt = QPushButton("Lấy Prompt Phân Tích Bible / Style")
        source_layout.addWidget(self.btn_gen_ai_prompt)
        layout.addWidget(source_group)

        # 2. Prompt Output
        prompt_group = QGroupBox("2. Prompt cho AI (Copy dán vào AI ngoài)")
        prompt_layout = QVBoxLayout(prompt_group)
        self.ai_prompt_output = QPlainTextEdit()
        self.ai_prompt_output.setReadOnly(True)
        self.ai_prompt_output.setMaximumHeight(150)
        prompt_layout.addWidget(self.ai_prompt_output)
        
        self.btn_copy_ai_prompt = QPushButton("Copy Prompt")
        prompt_layout.addWidget(self.btn_copy_ai_prompt)
        layout.addWidget(prompt_group)

        # 3. Result Input
        result_group = QGroupBox("3. Dán kết quả JSON từ AI")
        result_layout = QVBoxLayout(result_group)
        self.ai_result_input = QPlainTextEdit()
        self.ai_result_input.setPlaceholderText("Dán kết quả JSON ở đây...")
        result_layout.addWidget(self.ai_result_input)
        
        options_layout = QHBoxLayout()
        self.ai_overwrite_mode = QCheckBox("Ghi đè dữ liệu cũ (Overwrite)")
        self.ai_overwrite_mode.setToolTip("Nếu tắt, sẽ chỉ điền các trường còn trống (Merge)")
        options_layout.addWidget(self.ai_overwrite_mode)
        result_layout.addLayout(options_layout)
        
        self.btn_apply_ai_result = QPushButton("Áp dụng Bible / Style")
        result_layout.addWidget(self.btn_apply_ai_result)
        layout.addWidget(result_group)

        # Handlers
        self.btn_gen_ai_prompt.clicked.connect(self._on_gen_bible_style_prompt)
        self.btn_copy_ai_prompt.clicked.connect(self._on_copy_ai_prompt)
        self.btn_apply_ai_result.clicked.connect(self._on_apply_bible_style_result)

        return widget

    def refresh(self) -> None:
        self.char_list.clear()
        self.loc_list.clear()
        self.style_list.clear()
        self.ai_source_list.clear()

        if not self.app_state.project:
            return

        for char in self.app_state.project.characters:
            self.char_list.addItem(char.name)
        for loc in self.app_state.project.locations:
            self.loc_list.addItem(loc.name)
        for style in self.app_state.project.style_presets:
            self.style_list.addItem(style.name)
        
        for ch in self.app_state.project.source_chapters:
            item = f"Ch {ch.chapter_number}: {ch.title}"
            list_item = QListWidgetItem(item)
            list_item.setData(ITEM_ROLE, ch.chapter_id)
            self.ai_source_list.addItem(list_item)
            if ch.chapter_id in (self.app_state.selected_chapter_ids or []):
                list_item.setSelected(True)

    # ── Character handlers ──
    def _on_char_select(self, current, previous) -> None:
        if not current or not self.app_state.project:
            return
        name = current.text()
        for char in self.app_state.project.characters:
            if char.name == name:
                self.char_id.setText(char.character_id)
                self.char_name.setText(char.name)
                self.char_aliases.setText(", ".join(char.aliases))
                self.char_role.setText(char.role)
                self.char_gender.setText(char.gender)
                self.char_age.setText(char.age_description)
                self.char_personality.setText(char.personality)
                self.char_appearance.setPlainText(char.appearance)
                self.char_face.setText(char.face_details)
                self.char_hair.setText(char.hair)
                self.char_eyes.setText(char.eyes)
                self.char_body.setText(char.body_type)
                self.char_outfit.setText(char.default_outfit)
                self.char_outfit_variants.setText(", ".join(char.outfit_variants))
                self.char_prompt_base.setPlainText(char.visual_prompt_base)
                self.char_neg_terms.setText(", ".join(char.negative_prompt_terms))
                self.char_voice.setText(char.voice_notes)
                self.char_rel.setText(char.relationship_notes)
                self.char_tags.setText(", ".join(char.continuity_tags))
                
                # New fields
                self.char_sig_features.setText(char.signature_features)
                self.char_must_keep.setText(char.continuity_must_keep)
                self.char_forbidden.setText(char.continuity_forbidden)
                self.char_ref_note.setText(char.reference_image_note)
                
                self.char_ref_views.setText(char.required_views)
                self.char_ref_expr.setPlainText(char.expression_set)
                self.char_ref_micro.setText(char.micro_expression_set)
                self.char_ref_angles.setText(char.head_angle_views)
                self.char_ref_poses.setText(char.pose_set)
                self.char_ref_hands.setText(char.hand_gesture_set)
                self.char_ref_wardrobe.setPlainText(char.wardrobe_details)
                self.char_ref_props.setText(char.prop_details)
                self.char_ref_palette.setText(char.color_palette)
                self.char_ref_layout.setText(char.sheet_layout_style)
                self.char_ref_notes.setPlainText(char.reference_sheet_notes)
                break

    def _on_add_char(self) -> None:
        if not self.app_state.project:
            return
        name, ok = QInputDialog.getText(self, "Thêm nhân vật", "Tên nhân vật:")
        if ok and name:
            self.bible_controller.add_character(self.app_state.project, name=name)
            self.refresh_callback()

    def _on_del_char(self) -> None:
        current = self.char_list.currentItem()
        if not current or not self.app_state.project:
            return
        name = current.text()
        reply = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa nhân vật '{name}'?\nHành động này không thể hoàn tác.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.app_state.project.characters = [
                c for c in self.app_state.project.characters if c.name != name
            ]
            self.app_state.project.touch()
            self.refresh_callback()

    def _on_save_char(self) -> None:
        current = self.char_list.currentItem()
        if not current or not self.app_state.project:
            return
        char_id = self.char_id.text()
        for char in self.app_state.project.characters:
            if char.character_id == char_id:
                char.name = self.char_name.text()
                char.aliases = [s.strip() for s in self.char_aliases.text().split(",") if s.strip()]
                char.role = self.char_role.text()
                char.gender = self.char_gender.text()
                char.age_description = self.char_age.text()
                char.personality = self.char_personality.text()
                char.appearance = self.char_appearance.toPlainText()
                char.face_details = self.char_face.text()
                char.hair = self.char_hair.text()
                char.eyes = self.char_eyes.text()
                char.body_type = self.char_body.text()
                char.default_outfit = self.char_outfit.text()
                char.outfit_variants = [
                    s.strip() for s in self.char_outfit_variants.text().split(",") if s.strip()
                ]
                char.visual_prompt_base = self.char_prompt_base.toPlainText()
                char.negative_prompt_terms = [
                    s.strip() for s in self.char_neg_terms.text().split(",") if s.strip()
                ]
                char.voice_notes = self.char_voice.text()
                char.relationship_notes = self.char_rel.text()
                char.continuity_tags = [
                    s.strip() for s in self.char_tags.text().split(",") if s.strip()
                ]
                
                # New fields
                char.signature_features = self.char_sig_features.text()
                char.continuity_must_keep = self.char_must_keep.text()
                char.continuity_forbidden = self.char_forbidden.text()
                char.reference_image_note = self.char_ref_note.text()
                
                char.required_views = self.char_ref_views.text()
                char.expression_set = self.char_ref_expr.toPlainText()
                char.micro_expression_set = self.char_ref_micro.text()
                char.head_angle_views = self.char_ref_angles.text()
                char.pose_set = self.char_ref_poses.text()
                char.hand_gesture_set = self.char_ref_hands.text()
                char.wardrobe_details = self.char_ref_wardrobe.toPlainText()
                char.prop_details = self.char_ref_props.text()
                char.color_palette = self.char_ref_palette.text()
                char.sheet_layout_style = self.char_ref_layout.text()
                char.reference_sheet_notes = self.char_ref_notes.toPlainText()
                break
        self.app_state.project.touch()
        self.refresh_callback()

    # ── Location handlers ──
    def _on_loc_select(self, current, previous) -> None:
        if not current or not self.app_state.project:
            return
        name = current.text()
        for loc in self.app_state.project.locations:
            if loc.name == name:
                self.loc_id.setText(loc.location_id)
                self.loc_name.setText(loc.name)
                self.loc_aliases.setText(", ".join(loc.aliases))
                self.loc_type.setText(loc.location_type)
                self.loc_desc.setPlainText(loc.description)
                self.loc_mood.setText(loc.mood)
                self.loc_time.setText(loc.time_period)
                self.loc_lighting.setText(loc.lighting)
                self.loc_palette.setText(loc.color_palette)
                self.loc_arch.setText(loc.architecture_style)
                self.loc_props.setText(", ".join(loc.recurring_props))
                self.loc_prompt_base.setPlainText(loc.visual_prompt_base)
                self.loc_neg_terms.setText(", ".join(loc.negative_prompt_terms))
                self.loc_tags.setText(", ".join(loc.continuity_tags))
                break

    def _on_add_loc(self) -> None:
        if not self.app_state.project:
            return
        name, ok = QInputDialog.getText(self, "Thêm địa điểm", "Tên địa điểm:")
        if ok and name:
            self.bible_controller.add_location(self.app_state.project, name=name)
            self.refresh_callback()

    def _on_del_loc(self) -> None:
        current = self.loc_list.currentItem()
        if not current or not self.app_state.project:
            return
        name = current.text()
        reply = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa địa điểm '{name}'?\nHành động này không thể hoàn tác.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.app_state.project.locations = [
                l for l in self.app_state.project.locations if l.name != name
            ]
            self.app_state.project.touch()
            self.refresh_callback()

    def _on_save_loc(self) -> None:
        current = self.loc_list.currentItem()
        if not current or not self.app_state.project:
            return
        loc_id = self.loc_id.text()
        for loc in self.app_state.project.locations:
            if loc.location_id == loc_id:
                loc.name = self.loc_name.text()
                loc.aliases = [s.strip() for s in self.loc_aliases.text().split(",") if s.strip()]
                loc.location_type = self.loc_type.text()
                loc.description = self.loc_description = self.loc_desc.toPlainText()
                loc.mood = self.loc_mood.text()
                loc.time_period = self.loc_time.text()
                loc.lighting = self.loc_lighting.text()
                loc.color_palette = self.loc_palette.text()
                loc.architecture_style = self.loc_arch.text()
                loc.recurring_props = [
                    s.strip() for s in self.loc_props.text().split(",") if s.strip()
                ]
                loc.visual_prompt_base = self.loc_prompt_base.toPlainText()
                loc.negative_prompt_terms = [
                    s.strip() for s in self.loc_neg_terms.text().split(",") if s.strip()
                ]
                loc.continuity_tags = [
                    s.strip() for s in self.loc_tags.text().split(",") if s.strip()
                ]
                break
        self.app_state.project.touch()
        self.refresh_callback()

    # ── Style handlers ──
    def _on_style_select(self, current, previous) -> None:
        if not current or not self.app_state.project:
            return
        name = current.text()
        for style in self.app_state.project.style_presets:
            if style.name == name:
                self.style_id.setText(style.style_id)
                self.style_name.setText(style.name)
                self.style_desc.setPlainText(style.description)
                self.style_genre.setText(style.genre)
                self.style_pos.setPlainText(style.positive_prompt)
                self.style_neg.setPlainText(style.negative_prompt)
                self.style_line.setText(style.line_style)
                self.style_palette.setText(style.color_palette)
                self.style_lighting.setText(style.lighting_style)
                self.style_rendering.setText(style.rendering_style)
                self.style_char_rules.setText(style.character_design_rules)
                self.style_bg_detail.setText(style.background_detail_level)
                self.style_camera.setText(style.camera_style)
                self.style_mood_keys.setText(", ".join(style.mood_keywords))
                self.style_forbidden.setText(", ".join(style.forbidden_terms))
                break

    def _on_add_style(self) -> None:
        if not self.app_state.project:
            return
        name, ok = QInputDialog.getText(self, "Thêm Style", "Tên Style:")
        if ok and name:
            self.bible_controller.add_style_preset(self.app_state.project, name=name)
            self.refresh_callback()

    def _on_del_style(self) -> None:
        current = self.style_list.currentItem()
        if not current or not self.app_state.project:
            return
        name = current.text()
        if QMessageBox.question(self, "Xóa", f"Xóa '{name}'?") == QMessageBox.StandardButton.Yes:
            self.app_state.project.style_presets = [
                s for s in self.app_state.project.style_presets if s.name != name
            ]
            self.app_state.project.touch()
            self.refresh_callback()

    def _on_save_style(self) -> None:
        current = self.style_list.currentItem()
        if not current or not self.app_state.project:
            return
        style_id = self.style_id.text()
        for style in self.app_state.project.style_presets:
            if style.style_id == style_id:
                style.name = self.style_name.text()
                style.description = self.style_desc.toPlainText()
                style.genre = self.style_genre.text()
                style.positive_prompt = self.style_pos.toPlainText()
                style.negative_prompt = self.style_neg.toPlainText()
                style.line_style = self.style_line.text()
                style.color_palette = self.style_palette.text()
                style.lighting_style = self.style_lighting.text()
                style.rendering_style = self.style_rendering.text()
                style.character_design_rules = self.style_char_rules.text()
                style.background_detail_level = self.style_bg_detail.text()
                style.camera_style = self.style_camera.text()
                style.mood_keywords = [
                    s.strip() for s in self.style_mood_keys.text().split(",") if s.strip()
                ]
                style.forbidden_terms = [
                    s.strip() for s in self.style_forbidden.text().split(",") if s.strip()
                ]
                break
        self.app_state.project.touch()
        self.refresh_callback()

    def _on_set_default_style(self) -> None:
        current = self.style_list.currentItem()
        if not current or not self.app_state.project:
            return
        style_id = self.style_id.text()
        self.app_state.project.default_art_style = style_id
        self.app_state.project.touch()
        QMessageBox.information(self, "Thông báo", f"Đã đặt '{current.text()}' làm Style mặc định.")

    def _on_gen_default_styles(self) -> None:
        if not self.app_state.project:
            return
        self.bible_controller.create_default_style_presets(self.app_state.project)
        self.refresh_callback()

    def _on_build_ref_prompt(self) -> None:
        current = self.char_list.currentItem()
        if not current or not self.app_state.project:
            return
        char_id = self.char_id.text()
        
        # We need a style preset too. Use default for now.
        prompt = self.bible_controller.build_character_reference_prompt(
            self.app_state.project,
            char_id
        )
        
        # Copy to clipboard
        from PySide6.QtGui import QGuiApplication
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(prompt)
        
        QMessageBox.information(self, "Thành công", "Đã copy prompt tạo ảnh tham chiếu nhân vật vào Clipboard.")
        
        # Optional: Show in dialog for review
        from PySide6.QtWidgets import QDialog, QTextEdit, QVBoxLayout
        dialog = QDialog(self)
        dialog.setWindowTitle("Character Reference Sheet Prompt")
        dialog.resize(600, 400)
        d_layout = QVBoxLayout(dialog)
        edit = QTextEdit()
        edit.setPlainText(prompt)
        edit.setReadOnly(True)
        d_layout.addWidget(edit)
        
        close_btn = QPushButton("Đóng")
        close_btn.clicked.connect(dialog.accept)
        d_layout.addWidget(close_btn)
        
        dialog.exec()

    # ── AI Analysis handlers ──
    def _on_gen_bible_style_prompt(self) -> None:
        if not self.app_state.project: return
        selected_items = self.ai_source_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn ít nhất một chương nguồn.")
            return
            
        chapter_ids = [item.data(ITEM_ROLE) for item in selected_items]
        style_hint = self.ai_style_hint.text()
        
        prompt = self.bible_controller.build_bible_style_analysis_prompt(
            self.app_state.project,
            chapter_ids,
            style_hint
        )
        self.ai_prompt_output.setPlainText(prompt)

    def _on_copy_ai_prompt(self) -> None:
        self.ai_prompt_output.selectAll()
        self.ai_prompt_output.copy()
        QMessageBox.information(self, "Thông báo", "Đã copy prompt vào clipboard.")

    def _on_apply_bible_style_result(self) -> None:
        if not self.app_state.project: return
        result_text = self.ai_result_input.toPlainText().strip()
        if not result_text:
            QMessageBox.warning(self, "Lỗi", "Vui lòng dán kết quả JSON từ AI.")
            return
            
        overwrite = self.ai_overwrite_mode.isChecked()
        try:
            counts = self.bible_controller.apply_bible_style_analysis_result(
                self.app_state.project,
                result_text,
                overwrite=overwrite
            )
            msg = (f"Đã cập nhật Bible / Style:\n"
                   f"- Nhân vật: {counts['characters']}\n"
                   f"- Địa điểm: {counts['locations']}\n"
                   f"- Styles: {counts['styles']}")
            QMessageBox.information(self, "Thành công", msg)
            self.ai_result_input.clear()
            self.refresh_callback()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể áp dụng kết quả: {str(e)}")
