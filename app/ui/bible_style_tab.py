"""Tab for Character Bible, Location Bible, and Style Presets."""

from __future__ import annotations

import json
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

from app.domain.character import CharacterOutfit, CharacterVariant

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

        # Left: List of Base Characters
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        self.char_list = QListWidget()
        left_layout.addWidget(self.char_list)

        char_btn_layout = QHBoxLayout()
        self.btn_add_char = QPushButton("Thêm NV")
        self.btn_del_char = QPushButton("Xóa NV")
        char_btn_layout.addWidget(self.btn_add_char)
        char_btn_layout.addWidget(self.btn_del_char)
        left_layout.addLayout(char_btn_layout)
        layout.addWidget(left_widget, 1)

        # Right: Form Area (Scrollable)
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_scroll.setWidget(right_panel)
        layout.addWidget(right_scroll, 3)

        # 1. Base Character Identity Section (Small/Shared)
        core_group = QGroupBox("Core Identity (Shared)")
        core_layout = QGridLayout(core_group)
        self.char_id = QLineEdit(); self.char_id.setReadOnly(True)
        self.char_name = QLineEdit()
        self.char_aliases = QLineEdit()
        self.char_role = QLineEdit()
        self.char_gender = QLineEdit()
        self.char_age_desc = QLineEdit()
        self.char_personality = QLineEdit()
        self.char_rel = QLineEdit()
        self.char_tags = QLineEdit()

        r = 0
        r = self._add_row(core_layout, r, "ID:", self.char_id)
        r = self._add_row(core_layout, r, "Tên:", self.char_name)
        r = self._add_row(core_layout, r, "Bí danh:", self.char_aliases)
        r = self._add_row(core_layout, r, "Vai trò:", self.char_role)
        r = self._add_row(core_layout, r, "Giới tính:", self.char_gender)
        r = self._add_row(core_layout, r, "Tuổi (mô tả):", self.char_age_desc)
        r = self._add_row(core_layout, r, "Tính cách:", self.char_personality)
        r = self._add_row(core_layout, r, "Quan hệ:", self.char_rel)
        r = self._add_row(core_layout, r, "Tags:", self.char_tags)
        right_layout.addWidget(core_group)

        # 1.5 Visual Profile (for single-form characters)
        self.char_visual_container = QWidget()
        visual_v_layout = QVBoxLayout(self.char_visual_container)
        visual_v_layout.setContentsMargins(0,0,0,0)
        
        # Visual Group
        vis_group = QGroupBox("Visual Profile / Ngoại hình")
        vis_layout = QGridLayout(vis_group)
        self.char_app = QPlainTextEdit(); self.char_app.setMaximumHeight(60)
        self.char_face = QLineEdit()
        self.char_hair = QLineEdit()
        self.char_eyes = QLineEdit()
        self.char_body = QLineEdit()
        self.char_skin = QLineEdit()
        self.char_height = QLineEdit()
        self.char_prompt_base = QPlainTextEdit(); self.char_prompt_base.setMaximumHeight(60)
        self.char_sig = QLineEdit()
        
        r = 0
        r = self._add_row(vis_layout, r, "Appearance:", self.char_app)
        r = self._add_row(vis_layout, r, "Face Details:", self.char_face)
        r = self._add_row(vis_layout, r, "Hair:", self.char_hair)
        r = self._add_row(vis_layout, r, "Eyes:", self.char_eyes)
        r = self._add_row(vis_layout, r, "Body Type:", self.char_body)
        r = self._add_row(vis_layout, r, "Skin Tone:", self.char_skin)
        r = self._add_row(vis_layout, r, "Height:", self.char_height)
        r = self._add_row(vis_layout, r, "Prompt Base:", self.char_prompt_base)
        r = self._add_row(vis_layout, r, "Signature Features:", self.char_sig)
        visual_v_layout.addWidget(vis_group)
        
        # Outfit Group
        outfit_group = QGroupBox("Outfit / Trang phục")
        outfit_layout = QGridLayout(outfit_group)
        self.char_outfit = QLineEdit()
        self.char_outfit_det = QPlainTextEdit(); self.char_outfit_det.setMaximumHeight(60)
        self.char_outfit_col = QLineEdit()
        self.char_outfit_mat = QLineEdit()
        self.char_acc = QLineEdit()
        self.char_foot = QLineEdit()
        
        r = 0
        r = self._add_row(outfit_layout, r, "Default Outfit:", self.char_outfit)
        r = self._add_row(outfit_layout, r, "Outfit Details:", self.char_outfit_det)
        r = self._add_row(outfit_layout, r, "Colors:", self.char_outfit_col)
        r = self._add_row(outfit_layout, r, "Materials:", self.char_outfit_mat)
        r = self._add_row(outfit_layout, r, "Accessories:", self.char_acc)
        r = self._add_row(outfit_layout, r, "Footwear:", self.char_foot)
        visual_v_layout.addWidget(outfit_group)
        
        # Continuity Group
        cont_group = QGroupBox("Prompt / Continuity / Bảo toàn")
        cont_layout = QGridLayout(cont_group)
        self.char_keep = QLineEdit()
        self.char_forbid = QLineEdit()
        self.char_neg = QLineEdit()
        self.char_ref_note = QLineEdit()
        
        r = 0
        r = self._add_row(cont_layout, r, "Must Keep:", self.char_keep)
        r = self._add_row(cont_layout, r, "Forbidden:", self.char_forbid)
        r = self._add_row(cont_layout, r, "Negative Terms:", self.char_neg)
        r = self._add_row(cont_layout, r, "Reference Note:", self.char_ref_note)
        visual_v_layout.addWidget(cont_group)
        
        # Reference Sheet Group
        ref_group = QGroupBox("Reference Sheet Profile / Ảnh tham chiếu")
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
        r = self._add_row(ref_layout, r, "Sheet Layout:", self.char_ref_layout)
        r = self._add_row(ref_layout, r, "Reference Notes:", self.char_ref_notes)
        visual_v_layout.addWidget(ref_group)
        
        right_layout.addWidget(self.char_visual_container)

        # 2. Age-form Variant Tabs Section
        self.variant_container = QWidget()
        variant_v_layout = QVBoxLayout(self.variant_container)
        variant_v_layout.setContentsMargins(0,0,0,0)

        variant_header = QHBoxLayout()
        variant_header.addWidget(QLabel("<b>Age-form Variants / Hình thái tuổi:</b>"))
        self.btn_add_variant_ui = QPushButton("Thêm Hình thái (Variant)")
        self.btn_del_variant_ui = QPushButton("Xóa Hình thái")
        variant_header.addStretch()
        variant_header.addWidget(self.btn_add_variant_ui)
        variant_header.addWidget(self.btn_del_variant_ui)
        variant_v_layout.addLayout(variant_header)

        self.variant_tabs = QTabWidget()
        variant_v_layout.addWidget(self.variant_tabs)
        right_layout.addWidget(self.variant_container)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        self.btn_save_char = QPushButton("Lưu Nhân vật (Base + Variants)")
        self.btn_build_ref_prompt = QPushButton("Copy Prompt Ảnh Tham Chiếu (Selected Tab)")
        self.btn_build_ref_prompt.setObjectName("secondary-button")
        
        btn_layout.addWidget(self.btn_save_char)
        btn_layout.addWidget(self.btn_build_ref_prompt)
        right_layout.addLayout(btn_layout)

        # Advanced JSON (Optional/Hidden)
        self.json_toggle = QPushButton("Hiện/Ẩn JSON nâng cao")
        self.json_toggle.setCheckable(True)
        self.json_container = QWidget()
        self.json_container.setVisible(False)
        json_layout = QVBoxLayout(self.json_container)
        self.char_variants_json = QPlainTextEdit()
        self.char_variants_json.setMaximumHeight(100)
        json_layout.addWidget(QLabel("Raw Variants JSON:"))
        json_layout.addWidget(self.char_variants_json)
        right_layout.addWidget(self.json_toggle)
        right_layout.addWidget(self.json_container)

        # Signals
        self.char_list.currentItemChanged.connect(self._on_char_select)
        self.btn_add_char.clicked.connect(self._on_add_char)
        self.btn_del_char.clicked.connect(self._on_del_char)
        self.btn_save_char.clicked.connect(self._on_save_char)
        
        self.btn_add_variant_ui.clicked.connect(self._on_add_variant_tab)
        self.btn_del_variant_ui.clicked.connect(self._on_del_variant_tab)
        self.json_toggle.toggled.connect(self.json_container.setVisible)
        self.btn_build_ref_prompt.clicked.connect(self._on_build_ref_prompt)

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
                self._load_character_to_ui(char)
                break

    def _load_character_to_ui(self, char: Character) -> None:
        self.char_id.setText(char.character_id)
        self.char_name.setText(char.name)
        self.char_aliases.setText(", ".join(char.aliases))
        self.char_role.setText(char.role)
        self.char_gender.setText(char.gender)
        self.char_age_desc.setText(char.age_description)
        self.char_personality.setText(char.personality)
        self.char_rel.setText(char.relationship_notes)
        self.char_tags.setText(", ".join(char.continuity_tags))
        
        has_variants = len(char.variants) > 0
        self.char_visual_container.setVisible(not has_variants)
        self.variant_container.setVisible(has_variants)
        
        if not has_variants:
            # Load visual profile to main fields
            self.char_app.setPlainText(char.appearance)
            self.char_face.setText(char.face_details)
            self.char_hair.setText(char.hair)
            self.char_eyes.setText(char.eyes)
            self.char_body.setText(char.body_type)
            self.char_skin.setText(char.skin_tone)
            self.char_height.setText(char.height)
            self.char_prompt_base.setPlainText(char.visual_prompt_base)
            self.char_sig.setText(", ".join(char.signature_features))
            
            self.char_outfit.setText(char.default_outfit)
            self.char_outfit_det.setPlainText(char.outfit_details)
            self.char_outfit_col.setText(", ".join(char.outfit_colors))
            self.char_outfit_mat.setText(", ".join(char.outfit_materials))
            self.char_acc.setText(", ".join(char.accessories))
            self.char_foot.setText(char.footwear)
            
            self.char_keep.setText(", ".join(char.continuity_must_keep))
            self.char_forbid.setText(", ".join(char.continuity_forbidden))
            self.char_neg.setText(", ".join(char.negative_prompt_terms))
            self.char_ref_note.setText(char.reference_image_note)

            self.char_ref_views.setText(", ".join(char.required_views))
            self.char_ref_expr.setPlainText(", ".join(char.expression_set))
            self.char_ref_micro.setText(", ".join(char.micro_expression_set))
            self.char_ref_angles.setText(", ".join(char.head_angle_views))
            self.char_ref_poses.setText(", ".join(char.pose_set))
            self.char_ref_hands.setText(", ".join(char.hand_gesture_set))
            self.char_ref_wardrobe.setPlainText(", ".join(char.wardrobe_details))
            self.char_ref_props.setText(", ".join(char.prop_details))
            self.char_ref_palette.setText(", ".join(char.color_palette))
            self.char_ref_layout.setText(char.sheet_layout_style)
            self.char_ref_notes.setPlainText(char.reference_sheet_notes)

        # Clear and rebuild variant tabs
        self.variant_tabs.clear()
        for variant in char.variants:
            self._add_variant_tab(variant)
            
        self.char_variants_json.setPlainText(
            json.dumps(
                [item.to_dict() for item in char.variants],
                ensure_ascii=False,
                indent=2,
            )
        )

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
        
        # Build variants from tabs
        variants = []
        for i in range(self.variant_tabs.count()):
            tab = self.variant_tabs.widget(i)
            v = self._get_variant_data_from_tab(tab)
            if v:
                variants.append(v)

        has_variants = len(variants) > 0

        for char in self.app_state.project.characters:
            if char.character_id == char_id:
                char.name = self.char_name.text()
                char.aliases = [s.strip() for s in self.char_aliases.text().split(",") if s.strip()]
                char.role = self.char_role.text()
                char.gender = self.char_gender.text()
                char.age_description = self.char_age_desc.text()
                char.personality = self.char_personality.text()
                char.relationship_notes = self.char_rel.text()
                char.continuity_tags = [
                    s.strip() for s in self.char_tags.text().split(",") if s.strip()
                ]
                char.variants = variants
                
                if not has_variants:
                    # Save visual profile from main fields
                    char.appearance = self.char_app.toPlainText()
                    char.face_details = self.char_face.text()
                    char.hair = self.char_hair.text()
                    char.eyes = self.char_eyes.text()
                    char.body_type = self.char_body.text()
                    char.skin_tone = self.char_skin.text()
                    char.height = self.char_height.text()
                    char.visual_prompt_base = self.char_prompt_base.toPlainText()
                    char.signature_features = [s.strip() for s in self.char_sig.text().split(",") if s.strip()]
                    
                    char.default_outfit = self.char_outfit.text()
                    char.outfit_details = self.char_outfit_det.toPlainText()
                    char.outfit_colors = [s.strip() for s in self.char_outfit_col.text().split(",") if s.strip()]
                    char.outfit_materials = [s.strip() for s in self.char_outfit_mat.text().split(",") if s.strip()]
                    char.accessories = [s.strip() for s in self.char_acc.text().split(",") if s.strip()]
                    char.footwear = self.char_foot.text()
                    
                    char.continuity_must_keep = [s.strip() for s in self.char_keep.text().split(",") if s.strip()]
                    char.continuity_forbidden = [s.strip() for s in self.char_forbid.text().split(",") if s.strip()]
                    char.negative_prompt_terms = [s.strip() for s in self.char_neg.text().split(",") if s.strip()]
                    char.reference_image_note = self.char_ref_note.text()

                    def _csv(widget_text: str) -> list[str]:
                        return [s.strip() for s in widget_text.split(",") if s.strip()]

                    char.required_views = _csv(self.char_ref_views.text())
                    char.expression_set = _csv(self.char_ref_expr.toPlainText())
                    char.micro_expression_set = _csv(self.char_ref_micro.text())
                    char.head_angle_views = _csv(self.char_ref_angles.text())
                    char.pose_set = _csv(self.char_ref_poses.text())
                    char.hand_gesture_set = _csv(self.char_ref_hands.text())
                    char.wardrobe_details = _csv(self.char_ref_wardrobe.toPlainText())
                    char.prop_details = _csv(self.char_ref_props.text())
                    char.color_palette = _csv(self.char_ref_palette.text())
                    char.sheet_layout_style = self.char_ref_layout.text()
                    char.reference_sheet_notes = self.char_ref_notes.toPlainText()
                
                break
        self.app_state.project.touch()
        self.refresh_callback()

    def _on_add_variant_tab(self) -> None:
        if not self.char_id.text().strip():
            return
        char_id = self.char_id.text().strip()
        index = self.variant_tabs.count() + 1
        new_v = CharacterVariant(
            variant_id=f"{char_id}_v{index:02d}",
            character_id=char_id,
            display_name=f"Biến thể mới {index}"
        )
        self._add_variant_tab(new_v)
        self.variant_tabs.setCurrentIndex(self.variant_tabs.count() - 1)

    def _on_del_variant_tab(self) -> None:
        idx = self.variant_tabs.currentIndex()
        if idx < 0: return
        self.variant_tabs.removeTab(idx)

    def _add_variant_tab(self, variant: CharacterVariant) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Identify / Variant ID
        id_group = QGroupBox("Identity / Biến thể")
        id_layout = QGridLayout(id_group)
        
        v_id = QLineEdit(variant.variant_id); v_id.setObjectName("v_id")
        v_name = QLineEdit(variant.display_name); v_name.setObjectName("v_name")
        v_age_stage = QLineEdit(variant.age_stage); v_age_stage.setObjectName("v_age_stage")
        v_age_desc = QLineEdit(variant.age_description); v_age_desc.setObjectName("v_age_desc")
        v_gender = QLineEdit(variant.gender); v_gender.setObjectName("v_gender")
        
        r = 0
        r = self._add_row(id_layout, r, "Variant ID:", v_id)
        r = self._add_row(id_layout, r, "Display Name:", v_name)
        r = self._add_row(id_layout, r, "Age Stage:", v_age_stage)
        r = self._add_row(id_layout, r, "Age Description:", v_age_desc)
        r = self._add_row(id_layout, r, "Gender:", v_gender)
        layout.addWidget(id_group)
        
        # Visual Profile
        vis_group = QGroupBox("Visual Profile / Ngoại hình")
        vis_layout = QGridLayout(vis_group)
        v_app = QPlainTextEdit(variant.appearance); v_app.setObjectName("v_app"); v_app.setMaximumHeight(60)
        v_face = QLineEdit(variant.face_details); v_face.setObjectName("v_face")
        v_hair = QLineEdit(variant.hair); v_hair.setObjectName("v_hair")
        v_eyes = QLineEdit(variant.eyes); v_eyes.setObjectName("v_eyes")
        v_body = QLineEdit(variant.body_type); v_body.setObjectName("v_body")
        v_skin = QLineEdit(variant.skin_tone); v_skin.setObjectName("v_skin")
        v_height = QLineEdit(variant.height); v_height.setObjectName("v_height")
        v_prompt_base = QPlainTextEdit(variant.visual_prompt_base); v_prompt_base.setObjectName("v_prompt_base"); v_prompt_base.setMaximumHeight(60)
        v_sig = QLineEdit(", ".join(variant.signature_features)); v_sig.setObjectName("v_sig")
        
        r = 0
        r = self._add_row(vis_layout, r, "Appearance:", v_app)
        r = self._add_row(vis_layout, r, "Face Details:", v_face)
        r = self._add_row(vis_layout, r, "Hair:", v_hair)
        r = self._add_row(vis_layout, r, "Eyes:", v_eyes)
        r = self._add_row(vis_layout, r, "Body Type:", v_body)
        r = self._add_row(vis_layout, r, "Skin Tone:", v_skin)
        r = self._add_row(vis_layout, r, "Height:", v_height)
        r = self._add_row(vis_layout, r, "Prompt Base:", v_prompt_base)
        r = self._add_row(vis_layout, r, "Signature Features:", v_sig)
        layout.addWidget(vis_group)
        
        # Outfit
        outfit_group = QGroupBox("Outfit / Trang phục")
        outfit_layout = QGridLayout(outfit_group)
        v_outfit = QLineEdit(variant.default_outfit); v_outfit.setObjectName("v_outfit")
        v_outfit_det = QPlainTextEdit(variant.outfit_details); v_outfit_det.setObjectName("v_outfit_det"); v_outfit_det.setMaximumHeight(60)
        v_outfit_col = QLineEdit(", ".join(variant.outfit_colors)); v_outfit_col.setObjectName("v_outfit_col")
        v_outfit_mat = QLineEdit(", ".join(variant.outfit_materials)); v_outfit_mat.setObjectName("v_outfit_mat")
        v_acc = QLineEdit(", ".join(variant.accessories)); v_acc.setObjectName("v_acc")
        v_foot = QLineEdit(variant.footwear); v_foot.setObjectName("v_foot")
        
        r = 0
        r = self._add_row(outfit_layout, r, "Default Outfit:", v_outfit)
        r = self._add_row(outfit_layout, r, "Outfit Details:", v_outfit_det)
        r = self._add_row(outfit_layout, r, "Colors:", v_outfit_col)
        r = self._add_row(outfit_layout, r, "Materials:", v_outfit_mat)
        r = self._add_row(outfit_layout, r, "Accessories:", v_acc)
        r = self._add_row(outfit_layout, r, "Footwear:", v_foot)
        layout.addWidget(outfit_group)
        
        # Prompt / Continuity
        cont_group = QGroupBox("Prompt / Continuity / Bảo toàn")
        cont_layout = QGridLayout(cont_group)
        v_keep = QLineEdit(", ".join(variant.continuity_must_keep)); v_keep.setObjectName("v_keep")
        v_forbid = QLineEdit(", ".join(variant.continuity_forbidden)); v_forbid.setObjectName("v_forbid")
        v_neg = QLineEdit(", ".join(variant.negative_prompt_terms)); v_neg.setObjectName("v_neg")
        v_ref_note = QLineEdit(variant.reference_image_note); v_ref_note.setObjectName("v_ref_note")
        
        r = 0
        r = self._add_row(cont_layout, r, "Must Keep:", v_keep)
        r = self._add_row(cont_layout, r, "Forbidden:", v_forbid)
        r = self._add_row(cont_layout, r, "Negative Terms:", v_neg)
        r = self._add_row(cont_layout, r, "Reference Note:", v_ref_note)
        layout.addWidget(cont_group)
        
        # Reference Sheet Profile
        ref_group = QGroupBox("Reference Sheet Profile / Ảnh tham chiếu")
        ref_layout = QGridLayout(ref_group)
        v_ref_views = QLineEdit(variant.required_views); v_ref_views.setObjectName("v_ref_views")
        v_ref_expr = QPlainTextEdit(variant.expression_set); v_ref_expr.setObjectName("v_ref_expr"); v_ref_expr.setMaximumHeight(60)
        v_ref_micro = QLineEdit(variant.micro_expression_set); v_ref_micro.setObjectName("v_ref_micro")
        v_ref_angles = QLineEdit(variant.head_angle_views); v_ref_angles.setObjectName("v_ref_angles")
        v_ref_poses = QLineEdit(variant.pose_set); v_ref_poses.setObjectName("v_ref_poses")
        v_ref_hands = QLineEdit(variant.hand_gesture_set); v_ref_hands.setObjectName("v_ref_hands")
        v_ref_wardrobe = QPlainTextEdit(variant.wardrobe_details); v_ref_wardrobe.setObjectName("v_ref_wardrobe"); v_ref_wardrobe.setMaximumHeight(60)
        v_ref_props = QLineEdit(variant.prop_details); v_ref_props.setObjectName("v_ref_props")
        v_ref_palette = QLineEdit(variant.color_palette); v_ref_palette.setObjectName("v_ref_palette")
        v_ref_layout = QLineEdit(variant.sheet_layout_style); v_ref_layout.setObjectName("v_ref_layout")
        v_ref_notes = QPlainTextEdit(variant.reference_sheet_notes); v_ref_notes.setObjectName("v_ref_notes"); v_ref_notes.setMaximumHeight(60)
        
        r = 0
        r = self._add_row(ref_layout, r, "Required Views:", v_ref_views)
        r = self._add_row(ref_layout, r, "Expression Set:", v_ref_expr)
        r = self._add_row(ref_layout, r, "Micro Expressions:", v_ref_micro)
        r = self._add_row(ref_layout, r, "Head Angles:", v_ref_angles)
        r = self._add_row(ref_layout, r, "Pose Set:", v_ref_poses)
        r = self._add_row(ref_layout, r, "Hand Gestures:", v_ref_hands)
        r = self._add_row(ref_layout, r, "Wardrobe Details:", v_ref_wardrobe)
        r = self._add_row(ref_layout, r, "Prop Details:", v_ref_props)
        r = self._add_row(ref_layout, r, "Color Palette:", v_ref_palette)
        r = self._add_row(ref_layout, r, "Layout Style:", v_ref_layout)
        r = self._add_row(ref_layout, r, "General Notes:", v_ref_notes)
        layout.addWidget(ref_group)
        
        scroll.setWidget(container)
        tab_label = variant.display_name or variant.variant_id
        self.variant_tabs.addTab(scroll, tab_label)
        return scroll

    def _get_variant_data_from_tab(self, tab_widget: QWidget) -> CharacterVariant | None:
        if not isinstance(tab_widget, QScrollArea): return None
        container = tab_widget.widget()
        if not container: return None
        
        def find_child(name: str):
            return container.findChild(QWidget, name)
            
        def get_text(name: str) -> str:
            w = find_child(name)
            if isinstance(w, QLineEdit): return w.text()
            if isinstance(w, QPlainTextEdit): return w.toPlainText()
            return ""
            
        def get_list(name: str) -> list[str]:
            val = get_text(name)
            return [s.strip() for s in val.split(",") if s.strip()]

        return CharacterVariant(
            variant_id=get_text("v_id"),
            character_id=self.char_id.text(),
            display_name=get_text("v_name"),
            age_stage=get_text("v_age_stage"),
            age_description=get_text("v_age_desc"),
            gender=get_text("v_gender"),
            height=get_text("v_height"),
            face_details=get_text("v_face"),
            hair=get_text("v_hair"),
            eyes=get_text("v_eyes"),
            body_type=get_text("v_body"),
            skin_tone=get_text("v_skin"),
            appearance=get_text("v_app"),
            visual_prompt_base=get_text("v_prompt_base"),
            signature_features=get_list("v_sig"),
            default_outfit=get_text("v_outfit"),
            outfit_details=get_text("v_outfit_det"),
            outfit_colors=get_list("v_outfit_col"),
            outfit_materials=get_list("v_outfit_mat"),
            accessories=get_list("v_acc"),
            footwear=get_text("v_foot"),
            continuity_must_keep=get_list("v_keep"),
            continuity_forbidden=get_list("v_forbid"),
            negative_prompt_terms=get_list("v_neg"),
            reference_image_note=get_text("v_ref_note"),
            required_views=get_text("v_ref_views"),
            expression_set=get_text("v_ref_expr"),
            micro_expression_set=get_text("v_ref_micro"),
            head_angle_views=get_text("v_ref_angles"),
            pose_set=get_text("v_ref_poses"),
            hand_gesture_set=get_text("v_ref_hands"),
            wardrobe_details=get_text("v_ref_wardrobe"),
            prop_details=get_text("v_ref_props"),
            color_palette=get_text("v_ref_palette"),
            sheet_layout_style=get_text("v_ref_layout"),
            reference_sheet_notes=get_text("v_ref_notes")
        )

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
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một nhân vật trước.")
            return
        char_id = self.char_id.text()
        if not char_id:
            QMessageBox.warning(self, "Lỗi", "Không tìm thấy ID nhân vật.")
            return
        
        try:
            # Get selected variant_id from current tab
            idx = self.variant_tabs.currentIndex()
            variant_id = None
            if idx >= 0:
                tab = self.variant_tabs.widget(idx)
                v = self._get_variant_data_from_tab(tab)
                if v:
                    variant_id = v.variant_id
            
            # We need a style preset too. Use default for now.
            prompt = self.bible_controller.build_character_reference_prompt(
                self.app_state.project,
                char_id,
                variant_id=variant_id
            )
            
            if not prompt or not prompt.strip():
                QMessageBox.warning(self, "Lỗi", "Prompt được tạo ra bị trống. Vui lòng kiểm tra dữ liệu nhân vật.")
                return

            # Copy to clipboard
            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(prompt)
            
            # Show success and preview dialog
            from PySide6.QtWidgets import QDialog, QTextEdit, QVBoxLayout
            dialog = QDialog(self)
            dialog.setWindowTitle("Character Reference Sheet Prompt")
            dialog.resize(700, 500)
            d_layout = QVBoxLayout(dialog)
            
            info_label = QLabel("<b>Đã copy vào Clipboard!</b> Bạn có thể dán vào Stable Diffusion / Midjourney.")
            info_label.setStyleSheet("color: #4CAF50; margin-bottom: 5px;")
            d_layout.addWidget(info_label)
            
            edit = QTextEdit()
            edit.setPlainText(prompt)
            edit.setReadOnly(True)
            d_layout.addWidget(edit)
            
            close_btn = QPushButton("Đóng")
            close_btn.clicked.connect(dialog.accept)
            d_layout.addWidget(close_btn)
            
            dialog.exec()
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            QMessageBox.critical(self, "Lỗi hệ thống", f"Không thể tạo hoặc copy prompt:\n{str(e)}\n\nChi tiết:\n{error_details}")

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
