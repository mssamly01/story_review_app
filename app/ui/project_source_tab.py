"""Combined project and source chapter workflow tab."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
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
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from app.controllers.project_controller import ProjectController
    from app.domain.source_chapter import SourceChapter
    from app.ui.app_state import AppState


ITEM_ROLE = Qt.ItemDataRole.UserRole


class ProjectSourceTab(QWidget):
    def __init__(
        self,
        app_state: AppState,
        project_controller: ProjectController,
        refresh_callback: callable,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.project_controller = project_controller
        self.refresh_callback = refresh_callback
        self._is_refreshing = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(self._build_project_section())
        layout.addWidget(self._build_source_section(), 1)

    def _build_project_section(self) -> QGroupBox:
        group = QGroupBox("Dự án")
        layout = QGridLayout(group)

        self.title_edit = QLineEdit("Dự án không tên")
        self.genre_edit = QLineEdit()
        self.language_combo = QComboBox()
        self.language_combo.addItems(["vi", "en", "ja", "ko", "zh"])
        self.narration_combo = QComboBox()
        self.narration_combo.addItems(
            ["mysterious", "dramatic", "neutral", "humorous", "fast-paced"]
        )
        self.art_style_edit = QLineEdit("dark fantasy webtoon")
        self.path_label = QLabel("Chưa mở dự án nào")
        self.path_label.setWordWrap(True)

        layout.addWidget(QLabel("Tiêu đề"), 0, 0)
        layout.addWidget(self.title_edit, 0, 1)
        layout.addWidget(QLabel("Thể loại"), 0, 2)
        layout.addWidget(self.genre_edit, 0, 3)
        layout.addWidget(QLabel("Ngôn ngữ"), 1, 0)
        layout.addWidget(self.language_combo, 1, 1)
        layout.addWidget(QLabel("Phong cách kể mặc định"), 1, 2)
        layout.addWidget(self.narration_combo, 1, 3)
        layout.addWidget(QLabel("Art Style mặc định"), 2, 0)
        layout.addWidget(self.art_style_edit, 2, 1, 1, 3)

        button_layout = QHBoxLayout()
        self.btn_new = QPushButton("Mới")
        self.btn_open = QPushButton("Mở")
        self.btn_save = QPushButton("Lưu")
        self.btn_save_as = QPushButton("Lưu mới")
        for button in (self.btn_new, self.btn_open, self.btn_save, self.btn_save_as):
            button_layout.addWidget(button)
        button_layout.addStretch()
        layout.addLayout(button_layout, 3, 0, 1, 4)
        layout.addWidget(self.path_label, 4, 0, 1, 4)

        self.btn_new.clicked.connect(self._on_new_project)
        self.btn_open.clicked.connect(self._on_open_project)
        self.btn_save.clicked.connect(self._on_save_project)
        self.btn_save_as.clicked.connect(self._on_save_project_as)

        self.title_edit.textChanged.connect(self._sync_project_metadata)
        self.genre_edit.textChanged.connect(self._sync_project_metadata)
        self.language_combo.currentTextChanged.connect(self._sync_project_metadata)
        self.narration_combo.currentTextChanged.connect(self._sync_project_metadata)
        self.art_style_edit.textChanged.connect(self._sync_project_metadata)

        return group

    def _build_source_section(self) -> QGroupBox:
        group = QGroupBox("Nguồn chương truyện")
        outer_layout = QVBoxLayout(group)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Danh sách chương"))
        self.chapter_list = QListWidget()
        self.chapter_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        left_layout.addWidget(self.chapter_list, 1)

        left_buttons = QHBoxLayout()
        self.btn_add_blank_chapter = QPushButton("Thêm chương")
        self.btn_delete_chapter = QPushButton("Xóa chương")
        left_buttons.addWidget(self.btn_add_blank_chapter)
        left_buttons.addWidget(self.btn_delete_chapter)
        left_layout.addLayout(left_buttons)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        form = QGridLayout()
        self.chapter_title_edit = QLineEdit()
        self.chapter_number_spin = QSpinBox()
        self.chapter_number_spin.setRange(1, 9999)
        form.addWidget(QLabel("Tiêu đề chương"), 0, 0)
        form.addWidget(self.chapter_title_edit, 0, 1)
        form.addWidget(QLabel("Số chương"), 1, 0)
        form.addWidget(self.chapter_number_spin, 1, 1)
        right_layout.addLayout(form)

        right_layout.addWidget(QLabel("Nội dung gốc"))
        self.raw_text_edit = QPlainTextEdit()
        right_layout.addWidget(self.raw_text_edit, 1)

        right_buttons = QHBoxLayout()
        self.btn_save_chapter = QPushButton("Lưu chương")
        self.btn_add_file_chapter = QPushButton("Thêm chương từ tệp")
        right_buttons.addWidget(self.btn_save_chapter)
        right_buttons.addWidget(self.btn_add_file_chapter)
        right_buttons.addStretch()
        right_layout.addLayout(right_buttons)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)

        outer_layout.addWidget(splitter)

        self.chapter_list.currentItemChanged.connect(self._on_chapter_selected)
        self.chapter_list.itemSelectionChanged.connect(self._sync_selected_chapter_ids)
        self.btn_add_blank_chapter.clicked.connect(self._on_add_blank_chapter)
        self.btn_add_file_chapter.clicked.connect(self._on_add_chapter_from_file)
        self.btn_save_chapter.clicked.connect(self._on_save_chapter)
        self.btn_delete_chapter.clicked.connect(self._on_delete_chapter)

        return group

    def refresh(self) -> None:
        self._is_refreshing = True
        try:
            self._refresh_project_fields()
            self._refresh_chapter_list()
        finally:
            self._is_refreshing = False

    def _refresh_project_fields(self) -> None:
        project = self.app_state.project
        if not project:
            self.path_label.setText("Chưa mở dự án nào")
            return

        self.title_edit.setText(project.title)
        self.genre_edit.setText(getattr(project, "genre", "") or "")
        self.language_combo.setCurrentText(getattr(project, "language", "vi"))
        self.narration_combo.setCurrentText(
            getattr(project, "default_narration_style", "mysterious") or "mysterious"
        )
        self.art_style_edit.setText(getattr(project, "default_art_style", "") or "")
        path = self.app_state.project_path
        self.path_label.setText(str(path) if path else "Chưa lưu đường dẫn")

    def _refresh_chapter_list(self) -> None:
        self.chapter_list.clear()
        project = self.app_state.project
        if not project:
            self._clear_chapter_editor()
            return

        selected_id = self.app_state.selected_chapter_id
        if selected_id and not any(
            chapter.chapter_id == selected_id for chapter in project.source_chapters
        ):
            selected_id = None
            self.app_state.selected_chapter_id = None

        if selected_id is None and project.source_chapters:
            selected_id = project.source_chapters[0].chapter_id
            self.app_state.selected_chapter_id = selected_id

        selected_ids = set(self.app_state.selected_chapter_ids or [])
        if selected_id:
            selected_ids.add(selected_id)
        self.app_state.selected_chapter_ids = list(selected_ids)

        selected_item: QListWidgetItem | None = None
        for chapter in project.source_chapters:
            item = QListWidgetItem(f"{chapter.chapter_number} | {chapter.title}")
            item.setData(ITEM_ROLE, chapter.chapter_id)
            self.chapter_list.addItem(item)
            if chapter.chapter_id in selected_ids:
                item.setSelected(True)
            if chapter.chapter_id == selected_id:
                selected_item = item

        if selected_item is not None:
            self.chapter_list.setCurrentItem(selected_item)
            chapter = self._find_chapter(selected_id)
            if chapter:
                self._load_chapter(chapter)
        else:
            self._clear_chapter_editor()

    def _sync_project_metadata(self) -> None:
        if self._is_refreshing or not self.app_state.project:
            return
        project = self.app_state.project
        project.title = self.title_edit.text()
        project.genre = self.genre_edit.text()
        project.language = self.language_combo.currentText()
        project.default_narration_style = self.narration_combo.currentText()
        project.default_art_style = self.art_style_edit.text()
        project.touch()

    def _sync_selected_chapter_ids(self) -> None:
        if self._is_refreshing or not self.app_state.project:
            return
        self.app_state.selected_chapter_ids = [
            item.data(ITEM_ROLE) for item in self.chapter_list.selectedItems()
        ]

    def _on_chapter_selected(
        self, current: QListWidgetItem | None, previous: QListWidgetItem | None
    ) -> None:
        if self._is_refreshing:
            return
        if current is None:
            self.app_state.selected_chapter_id = None
            self.app_state.selected_chapter_ids = []
            self._clear_chapter_editor()
            return
        chapter_id = current.data(ITEM_ROLE)
        self.app_state.selected_chapter_id = chapter_id
        self._sync_selected_chapter_ids()
        chapter = self._find_chapter(chapter_id)
        if chapter:
            self._load_chapter(chapter)

    def _load_chapter(self, chapter: SourceChapter) -> None:
        self.chapter_title_edit.setText(chapter.title)
        self.chapter_number_spin.setValue(int(chapter.chapter_number))
        self.raw_text_edit.setPlainText(chapter.raw_text)

    def _clear_chapter_editor(self) -> None:
        self.chapter_title_edit.clear()
        self.chapter_number_spin.setValue(1)
        self.raw_text_edit.clear()

    def _find_chapter(self, chapter_id: str | None) -> SourceChapter | None:
        if not chapter_id or not self.app_state.project:
            return None
        for chapter in self.app_state.project.source_chapters:
            if chapter.chapter_id == chapter_id:
                return chapter
        return None

    def _on_new_project(self) -> None:
        try:
            self.project_controller.create_project(
                self.title_edit.text().strip() or "Dự án không tên",
                genre=self.genre_edit.text(),
                language=self.language_combo.currentText(),
                default_narration_style=self.narration_combo.currentText(),
                default_art_style=self.art_style_edit.text(),
            )
            self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_open_project(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Mở dự án",
            "",
            "Project JSON (*.json)",
        )
        if not path:
            return
        try:
            self.project_controller.open_project(path)
            self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_save_project(self) -> None:
        if not self.app_state.project_path:
            self._on_save_project_as()
            return
        try:
            self.project_controller.save_project()
            self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_save_project_as(self) -> None:
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Lưu dự án",
            "",
            "Project JSON (*.json)",
        )
        if not path:
            return
        try:
            self.project_controller.save_project(path)
            self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_add_blank_chapter(self) -> None:
        if not self.app_state.project:
            QMessageBox.warning(self, "Cảnh báo", "Hãy tạo hoặc mở dự án trước.")
            return
        chapter_number = len(self.app_state.project.source_chapters) + 1
        try:
            chapter = self.project_controller.add_chapter(
                title=f"Chương {chapter_number}",
                chapter_number=chapter_number,
                raw_text="",
            )
            self.app_state.selected_chapter_id = chapter.chapter_id
            self.app_state.selected_chapter_ids = [chapter.chapter_id]
            self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_add_chapter_from_file(self) -> None:
        if not self.app_state.project:
            QMessageBox.warning(self, "Cảnh báo", "Hãy tạo hoặc mở dự án trước.")
            return
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Thêm chương nguồn",
            "",
            "Tệp văn bản (*.txt);;All Files (*)",
        )
        if not path:
            return
        source_path = Path(path)
        chapter_number = len(self.app_state.project.source_chapters) + 1
        try:
            chapter = self.project_controller.add_chapter_from_file(
                title=source_path.stem,
                chapter_number=chapter_number,
                text_file=source_path,
            )
            self.app_state.selected_chapter_id = chapter.chapter_id
            self.app_state.selected_chapter_ids = [chapter.chapter_id]
            self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_save_chapter(self) -> None:
        chapter_id = self.app_state.selected_chapter_id
        if not chapter_id:
            return
        try:
            self.project_controller.update_chapter(
                chapter_id,
                title=self.chapter_title_edit.text(),
                chapter_number=self.chapter_number_spin.value(),
                raw_text=self.raw_text_edit.toPlainText(),
            )
            self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_delete_chapter(self) -> None:
        if not self.app_state.project or not self.app_state.selected_chapter_id:
            QMessageBox.warning(self, "Cảnh báo", "Hãy chọn chương cần xóa.")
            return

        chapter_id = self.app_state.selected_chapter_id
        chapter = self._find_chapter(chapter_id)
        chapter_name = chapter.title if chapter else chapter_id
        reply = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa chương '{chapter_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self.project_controller.delete_chapter(chapter_id)
            self.app_state.selected_chapter_id = None
            self.app_state.selected_chapter_ids = []
            self._clear_chapter_editor()
            self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))
