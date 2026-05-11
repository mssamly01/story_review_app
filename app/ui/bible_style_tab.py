"""Tab for Character Bible, Location Bible, and Style Presets."""

from __future__ import annotations

from typing import TYPE_CHECKING
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QInputDialog,
    QMessageBox,
)

if TYPE_CHECKING:
    from app.ui.app_state import AppState
    from app.controllers.bible_controller import BibleController

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
        
        layout.addWidget(self.tabs)

    def _build_character_bible(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Left: List and basic buttons
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
        
        # Right: Form
        form = QWidget()
        form_layout = QGridLayout(form)
        self.char_name = QLineEdit()
        self.char_role = QLineEdit()
        self.char_appearance = QPlainTextEdit()
        self.char_appearance.setMaximumHeight(80)
        self.char_prompt_base = QPlainTextEdit()
        self.char_prompt_base.setMaximumHeight(80)
        
        form_layout.addWidget(QLabel("Tên:"), 0, 0)
        form_layout.addWidget(self.char_name, 0, 1)
        form_layout.addWidget(QLabel("Vai trò:"), 1, 0)
        form_layout.addWidget(self.char_role, 1, 1)
        form_layout.addWidget(QLabel("Ngoại hình:"), 2, 0)
        form_layout.addWidget(self.char_appearance, 2, 1)
        form_layout.addWidget(QLabel("Visual Prompt Base:"), 3, 0)
        form_layout.addWidget(self.char_prompt_base, 3, 1)
        
        self.btn_save_char = QPushButton("Lưu nhân vật")
        form_layout.addWidget(self.btn_save_char, 4, 0, 1, 2)
        
        layout.addWidget(form, 2)
        
        # Connect signals
        self.char_list.currentItemChanged.connect(self._on_char_select)
        self.btn_add_char.clicked.connect(self._on_add_char)
        self.btn_del_char.clicked.connect(self._on_del_char)
        self.btn_save_char.clicked.connect(self._on_save_char)
        
        return widget

    def _build_location_bible(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Left: List and basic buttons
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
        
        # Right: Form
        form = QWidget()
        form_layout = QGridLayout(form)
        self.loc_name = QLineEdit()
        self.loc_mood = QLineEdit()
        self.loc_prompt_base = QPlainTextEdit()
        self.loc_prompt_base.setMaximumHeight(80)
        
        form_layout.addWidget(QLabel("Tên:"), 0, 0)
        form_layout.addWidget(self.loc_name, 0, 1)
        form_layout.addWidget(QLabel("Tâm trạng (Mood):"), 1, 0)
        form_layout.addWidget(self.loc_mood, 1, 1)
        form_layout.addWidget(QLabel("Visual Prompt Base:"), 2, 0)
        form_layout.addWidget(self.loc_prompt_base, 2, 1)
        
        self.btn_save_loc = QPushButton("Lưu địa điểm")
        form_layout.addWidget(self.btn_save_loc, 3, 0, 1, 2)
        
        layout.addWidget(form, 2)
        
        # Connect signals
        self.loc_list.currentItemChanged.connect(self._on_loc_select)
        self.btn_add_loc.clicked.connect(self._on_add_loc)
        self.btn_del_loc.clicked.connect(self._on_del_loc)
        self.btn_save_loc.clicked.connect(self._on_save_loc)
        
        return widget

    def _build_style_presets(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        self.style_list = QListWidget()
        layout.addWidget(self.style_list, 1)
        
        form = QWidget()
        form_layout = QVBoxLayout(form)
        self.btn_gen_default_styles = QPushButton("Tạo các Style mặc định")
        form_layout.addWidget(self.btn_gen_default_styles)
        form_layout.addStretch()
        
        layout.addWidget(form, 2)
        
        self.btn_gen_default_styles.clicked.connect(self._on_gen_default_styles)
        
        return widget

    def refresh(self) -> None:
        self.char_list.clear()
        self.loc_list.clear()
        self.style_list.clear()
        
        if not self.app_state.project:
            return
            
        for char in self.app_state.project.characters:
            self.char_list.addItem(char.name)
        for loc in self.app_state.project.locations:
            self.loc_list.addItem(loc.name)
        for style in self.app_state.project.style_presets:
            self.style_list.addItem(style.name)

    # ── Character handlers ──
    def _on_char_select(self, current, previous) -> None:
        if not current or not self.app_state.project:
            return
        name = current.text()
        for char in self.app_state.project.characters:
            if char.name == name:
                self.char_name.setText(char.name)
                self.char_role.setText(getattr(char, "role", "") or "")
                self.char_appearance.setPlainText(getattr(char, "appearance", "") or "")
                self.char_prompt_base.setPlainText(getattr(char, "visual_prompt_base", "") or "")
                break

    def _on_add_char(self) -> None:
        if not self.app_state.project:
            return
        name, ok = QInputDialog.getText(self, "Thêm nhân vật", "Tên nhân vật:")
        if ok and name:
            try:
                self.bible_controller.add_character(self.app_state.project, name=name)
                self.refresh_callback()
            except Exception as exc:
                QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_del_char(self) -> None:
        current = self.char_list.currentItem()
        if not current or not self.app_state.project:
            return
        name = current.text()
        self.app_state.project.characters = [
            c for c in self.app_state.project.characters if c.name != name
        ]
        self.app_state.project.touch()
        self.refresh_callback()

    def _on_save_char(self) -> None:
        current = self.char_list.currentItem()
        if not current or not self.app_state.project:
            return
        old_name = current.text()
        for char in self.app_state.project.characters:
            if char.name == old_name:
                char.name = self.char_name.text()
                if hasattr(char, "role"): char.role = self.char_role.text()
                char.appearance = self.char_appearance.toPlainText()
                char.visual_prompt_base = self.char_prompt_base.toPlainText()
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
                self.loc_name.setText(loc.name)
                self.loc_mood.setText(getattr(loc, "mood", "") or "")
                self.loc_prompt_base.setPlainText(getattr(loc, "visual_prompt_base", "") or "")
                break

    def _on_add_loc(self) -> None:
        if not self.app_state.project:
            return
        name, ok = QInputDialog.getText(self, "Thêm địa điểm", "Tên địa điểm:")
        if ok and name:
            try:
                self.bible_controller.add_location(self.app_state.project, name=name)
                self.refresh_callback()
            except Exception as exc:
                QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_del_loc(self) -> None:
        current = self.loc_list.currentItem()
        if not current or not self.app_state.project:
            return
        name = current.text()
        self.app_state.project.locations = [
            loc for loc in self.app_state.project.locations if loc.name != name
        ]
        self.app_state.project.touch()
        self.refresh_callback()

    def _on_save_loc(self) -> None:
        current = self.loc_list.currentItem()
        if not current or not self.app_state.project:
            return
        old_name = current.text()
        for loc in self.app_state.project.locations:
            if loc.name == old_name:
                loc.name = self.loc_name.text()
                if hasattr(loc, "mood"): loc.mood = self.loc_mood.text()
                loc.visual_prompt_base = self.loc_prompt_base.toPlainText()
                break
        self.app_state.project.touch()
        self.refresh_callback()

    def _on_gen_default_styles(self) -> None:
        if not self.app_state.project:
            return
        try:
            self.bible_controller.create_default_style_presets(self.app_state.project)
            self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))
