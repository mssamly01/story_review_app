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
        self.char_list = QListWidget()
        layout.addWidget(self.char_list, 1)
        
        form = QWidget()
        form_layout = QGridLayout(form)
        self.char_name = QLineEdit()
        self.char_appearance = QPlainTextEdit()
        self.char_prompt_base = QPlainTextEdit()
        
        form_layout.addWidget(QLabel("Tên:"), 0, 0)
        form_layout.addWidget(self.char_name, 0, 1)
        form_layout.addWidget(QLabel("Ngoại hình:"), 1, 0)
        form_layout.addWidget(self.char_appearance, 1, 1)
        form_layout.addWidget(QLabel("Visual Prompt Base:"), 2, 0)
        form_layout.addWidget(self.char_prompt_base, 2, 1)
        
        layout.addWidget(form, 2)
        return widget

    def _build_location_bible(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        self.loc_list = QListWidget()
        layout.addWidget(self.loc_list, 1)
        
        form = QWidget()
        form_layout = QGridLayout(form)
        self.loc_name = QLineEdit()
        self.loc_prompt_base = QPlainTextEdit()
        
        form_layout.addWidget(QLabel("Tên:"), 0, 0)
        form_layout.addWidget(self.loc_name, 0, 1)
        form_layout.addWidget(QLabel("Visual Prompt Base:"), 1, 0)
        form_layout.addWidget(self.loc_prompt_base, 1, 1)
        
        layout.addWidget(form, 2)
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
