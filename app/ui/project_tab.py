"""Project management tab."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from app.controllers.project_controller import ProjectController
    from app.ui.app_state import AppState


class ProjectTab(QWidget):
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
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # --- Project Info Group ---
        info_group = QGroupBox("Thông tin dự án")
        info_layout = QGridLayout(info_group)

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

        info_layout.addWidget(QLabel("Tiêu đề:"), 0, 0)
        info_layout.addWidget(self.title_edit, 0, 1)
        info_layout.addWidget(QLabel("Thể loại:"), 1, 0)
        info_layout.addWidget(self.genre_edit, 1, 1)
        info_layout.addWidget(QLabel("Ngôn ngữ:"), 2, 0)
        info_layout.addWidget(self.language_combo, 2, 1)
        info_layout.addWidget(QLabel("Phong cách kể:"), 3, 0)
        info_layout.addWidget(self.narration_combo, 3, 1)
        info_layout.addWidget(QLabel("Art Style:"), 4, 0)
        info_layout.addWidget(self.art_style_edit, 4, 1)

        btn_layout = QGridLayout()
        self.btn_new = QPushButton("Mới")
        self.btn_open = QPushButton("Mở")
        self.btn_save = QPushButton("Lưu")
        self.btn_save_as = QPushButton("Lưu mới")

        btn_layout.addWidget(self.btn_new, 0, 0)
        btn_layout.addWidget(self.btn_open, 0, 1)
        btn_layout.addWidget(self.btn_save, 0, 2)
        btn_layout.addWidget(self.btn_save_as, 0, 3)

        info_layout.addLayout(btn_layout, 5, 0, 1, 2)
        info_layout.addWidget(self.path_label, 6, 0, 1, 2)
        layout.addWidget(info_group)

        # --- AI Settings Group ---
        ai_group = QGroupBox("Cấu hình AI")
        ai_layout = QGridLayout(ai_group)

        self.ai_mode_combo = QComboBox()
        self.ai_mode_combo.addItems(["deterministic", "mock", "real"])
        self.model_edit = QLineEdit()

        ai_layout.addWidget(QLabel("Chế độ AI:"), 0, 0)
        ai_layout.addWidget(self.ai_mode_combo, 0, 1)
        ai_layout.addWidget(QLabel("Model (nếu có):"), 1, 0)
        ai_layout.addWidget(self.model_edit, 1, 1)
        layout.addWidget(ai_group)

        layout.addStretch()

        # Connect signals
        self.btn_new.clicked.connect(self._on_new)
        self.btn_open.clicked.connect(self._on_open)
        self.btn_save.clicked.connect(self._on_save)
        self.btn_save_as.clicked.connect(self._on_save_as)
        self.ai_mode_combo.currentTextChanged.connect(self._on_ai_mode_changed)
        self.model_edit.textChanged.connect(self._on_model_changed)

        # Sync metadata
        self.title_edit.textChanged.connect(self._sync_project_metadata)
        self.genre_edit.textChanged.connect(self._sync_project_metadata)
        self.language_combo.currentTextChanged.connect(self._sync_project_metadata)
        self.narration_combo.currentTextChanged.connect(self._sync_project_metadata)
        self.art_style_edit.textChanged.connect(self._sync_project_metadata)

    def refresh(self) -> None:
        if self.app_state.project:
            p = self.app_state.project
            self.title_edit.setText(p.title)
            self.genre_edit.setText(getattr(p, "genre", "") or "")
            self.language_combo.setCurrentText(getattr(p, "language", "vi"))
            self.narration_combo.setCurrentText(getattr(p, "default_narration_style", "neutral"))
            self.art_style_edit.setText(getattr(p, "default_art_style", "") or "")
            self.path_label.setText(str(self.app_state.project_path or ""))
        else:
            self.path_label.setText("Chưa mở dự án nào")

        self.ai_mode_combo.setCurrentText(self.app_state.ai_mode)
        self.model_edit.setText(self.app_state.model or "")

    def _sync_project_metadata(self) -> None:
        if not self.app_state.project:
            return
        p = self.app_state.project
        p.title = self.title_edit.text()
        p.genre = self.genre_edit.text()
        p.language = self.language_combo.currentText()
        p.default_narration_style = self.narration_combo.currentText()
        p.default_art_style = self.art_style_edit.text()
        p.touch()

    def _on_new(self) -> None:
        try:
            self.project_controller.create_project(
                self.title_edit.text(),
                genre=self.genre_edit.text(),
                language=self.language_combo.currentText(),
                default_narration_style=self.narration_combo.currentText(),
                default_art_style=self.art_style_edit.text(),
            )
            self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Mở dự án", "", "Project JSON (*.json)")
        if path:
            try:
                self.project_controller.open_project(path)
                self.refresh_callback()
            except Exception as exc:
                QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_save(self) -> None:
        if not self.app_state.project_path:
            self._on_save_as()
            return
        try:
            self.project_controller.save_project()
            self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Lưu dự án", "", "Project JSON (*.json)")
        if path:
            try:
                self.project_controller.save_project(path)
                self.refresh_callback()
            except Exception as exc:
                QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_ai_mode_changed(self, mode: str) -> None:
        self.app_state.ai_mode = mode

    def _on_model_changed(self, model: str) -> None:
        self.app_state.model = model if model.strip() else None
