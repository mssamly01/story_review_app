"""Source chapter management tab."""

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
    QSplitter,
    QVBoxLayout,
    QWidget,
    QSpinBox,
    QMessageBox,
    QInputDialog,
    QFileDialog,
)

if TYPE_CHECKING:
    from app.ui.app_state import AppState
    from app.controllers.project_controller import ProjectController
    from app.controllers.generation_controller import GenerationController

ITEM_ROLE = Qt.ItemDataRole.UserRole


class SourceTab(QWidget):
    def __init__(
        self,
        app_state: AppState,
        project_controller: ProjectController,
        generation_controller: GenerationController,
        refresh_callback: callable,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.project_controller = project_controller
        self.generation_controller = generation_controller
        self.refresh_callback = refresh_callback
        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- Left: Chapter List ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(QLabel("Danh sách chương nguồn"))
        self.chapter_list = QListWidget()
        left_layout.addWidget(self.chapter_list)
        
        self.btn_add = QPushButton("Thêm từ tệp")
        left_layout.addWidget(self.btn_add)
        splitter.addWidget(left_widget)

        # --- Right: Editor ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        form_layout = QGridLayout()
        self.title_edit = QLineEdit()
        self.number_spin = QSpinBox()
        self.number_spin.setRange(1, 9999)
        
        form_layout.addWidget(QLabel("Tiêu đề:"), 0, 0)
        form_layout.addWidget(self.title_edit, 0, 1)
        form_layout.addWidget(QLabel("Số chương:"), 1, 0)
        form_layout.addWidget(self.number_spin, 1, 1)
        right_layout.addLayout(form_layout)

        self.raw_text_edit = QPlainTextEdit()
        right_layout.addWidget(QLabel("Nội dung thô:"))
        right_layout.addWidget(self.raw_text_edit)

        action_layout = QHBoxLayout()
        self.btn_save = QPushButton("Lưu thay đổi")
        self.btn_parse = QPushButton("Phân tích truyện (Parse)")
        action_layout.addWidget(self.btn_save)
        action_layout.addWidget(self.btn_parse)
        right_layout.addLayout(action_layout)
        
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter)

        # Connect signals
        self.chapter_list.currentItemChanged.connect(self._on_chapter_select)
        self.btn_add.clicked.connect(self._on_add_chapter)
        self.btn_save.clicked.connect(self._on_save_edits)
        self.btn_parse.clicked.connect(self._on_parse)

    def refresh(self) -> None:
        self.chapter_list.clear()
        if not self.app_state.project:
            self._clear_editor()
            return

        for chapter in self.app_state.project.source_chapters:
            item = QListWidgetItem(f"{chapter.chapter_number} | {chapter.title}")
            item.setData(ITEM_ROLE, chapter.chapter_id)
            self.chapter_list.addItem(item)
            if chapter.chapter_id == self.app_state.selected_chapter_id:
                self.chapter_list.setCurrentItem(item)
                self._load_chapter(chapter)

    def _clear_editor(self) -> None:
        self.title_edit.clear()
        self.number_spin.setValue(1)
        self.raw_text_edit.clear()

    def _load_chapter(self, chapter) -> None:
        self.title_edit.setText(chapter.title)
        self.number_spin.setValue(int(chapter.chapter_number))
        self.raw_text_edit.setPlainText(chapter.raw_text)

    def _on_chapter_select(self, current: QListWidgetItem | None, previous: object) -> None:
        if not current:
            self.app_state.selected_chapter_id = None
            return
        
        chapter_id = current.data(ITEM_ROLE)
        self.app_state.selected_chapter_id = chapter_id
        chapter = self.project_controller.find_chapter(chapter_id)
        if chapter:
            self._load_chapter(chapter)

    def _on_add_chapter(self) -> None:
        if not self.app_state.project:
            QMessageBox.warning(self, "Cảnh báo", "Hãy tạo hoặc mở dự án trước.")
            return

        path, _ = QFileDialog.getOpenFileName(self, "Thêm chương nguồn", "", "Tệp văn bản (*.txt)")
        if not path:
            return
        
        title, ok = QInputDialog.getText(self, "Tiêu đề chương", "Nhập tiêu đề chương:")
        if not ok or not title:
            return
            
        num, ok = QInputDialog.getInt(self, "Số chương", "Nhập số thứ tự chương:", 1, 1, 9999)
        if not ok:
            return

        try:
            self.project_controller.add_chapter_from_file(title, num, path)
            self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_save_edits(self) -> None:
        if not self.app_state.selected_chapter_id:
            return
        
        try:
            self.project_controller.update_chapter(
                self.app_state.selected_chapter_id,
                title=self.title_edit.text(),
                chapter_number=self.number_spin.value(),
                raw_text=self.raw_text_edit.toPlainText(),
            )
            QMessageBox.information(self, "Thông báo", "Đã lưu thay đổi.")
            self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_parse(self) -> None:
        if not self.app_state.selected_chapter_id:
            return
        
        try:
            self.generation_controller.parse_story(
                self.app_state.project,
                self.app_state.selected_chapter_id,
                ai_mode=self.app_state.ai_mode,
                model=self.app_state.model,
            )
            QMessageBox.information(self, "Thông báo", "Phân tích chương thành công.")
            self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))
