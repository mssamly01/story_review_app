"""Main PySide6 window for the minimal desktop UI."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QWidget,
)

from app.controllers.export_controller import ExportController
from app.controllers.export_profile_controller import ExportProfileController
from app.controllers.generation_controller import GenerationController
from app.controllers.project_controller import ProjectController
from app.domain.beat import Beat
from app.domain.scene import Scene
from app.ui.beat_browser import BeatBrowser
from app.ui.beat_editor import BeatEditor
from app.ui.episode_panel import EpisodePanel
from app.ui.export_panel import ExportPanel
from app.ui.project_panel import ProjectPanel
from app.ui.source_chapter_panel import SourceChapterPanel


class MainWindow(QMainWindow):
    def __init__(
        self,
        parent: QWidget | None = None,
        project_controller: ProjectController | None = None,
        generation_controller: GenerationController | None = None,
        export_controller: ExportController | None = None,
        export_profile_controller: ExportProfileController | None = None,
    ) -> None:
        super().__init__(parent)
        self.project_controller = project_controller or ProjectController()
        self.generation_controller = generation_controller or GenerationController(
            self.project_controller.project_service
        )
        self.export_controller = export_controller or ExportController(
            self.project_controller.project_service
        )
        self.export_profile_controller = (
            export_profile_controller
            or ExportProfileController(self.project_controller.project_service)
        )
        self.selected_chapter_id: str | None = None
        self.selected_episode_id: str | None = None
        self.selected_scene_id: str | None = None
        self.selected_beat_id: str | None = None

        self.setWindowTitle("Story Review Studio")
        self.resize(1320, 820)
        self._build_layout()
        self._load_export_profiles()

    def _build_layout(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QGridLayout(central)

        self.project_panel = ProjectPanel(
            central,
            {
                "new_project": self.new_project,
                "open_project": self.open_project,
                "save_project": self.save_project,
                "save_project_as": self.save_project_as,
            },
        )
        layout.addWidget(self.project_panel, 0, 0, 1, 3)

        self.source_panel = SourceChapterPanel(
            central,
            {
                "add_chapter": self.add_chapter,
                "select_chapter": self.select_chapter,
                "update_chapter": self.update_chapter,
            },
        )
        layout.addWidget(self.source_panel, 1, 0)

        self.episode_panel = EpisodePanel(
            central,
            {
                "plan_episode": self.plan_episode,
                "run_pipeline": self.run_full_pipeline,
                "select_episode": self.select_episode,
            },
        )
        layout.addWidget(self.episode_panel, 1, 1)

        self.browser = BeatBrowser(
            central,
            {
                "select_scene": self.select_scene,
                "select_beat": self.select_beat,
            },
        )
        layout.addWidget(self.browser, 2, 0, 1, 2)

        self.beat_editor = BeatEditor(
            central,
            {
                "update_beat": self.update_beat,
            },
        )
        layout.addWidget(self.beat_editor, 1, 2, 2, 1)

        layout.addWidget(self._pipeline_group(), 3, 0, 1, 2)

        self.export_panel = ExportPanel(
            central,
            {
                "export_episode": self.export_episode,
                "export_profile": self.export_profile,
            },
        )
        layout.addWidget(self.export_panel, 3, 2)

        self.status_area = QPlainTextEdit()
        self.status_area.setReadOnly(True)
        self.status_area.setMaximumHeight(96)
        layout.addWidget(self.status_area, 4, 0, 1, 3)
        self.set_status("Ready")

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.setRowStretch(1, 1)
        layout.setRowStretch(2, 1)

    def _pipeline_group(self) -> QGroupBox:
        group = QGroupBox("Pipeline")
        layout = QGridLayout(group)
        buttons = [
            ("Parse Story", self.parse_story),
            ("Generate Beats", self.generate_beats),
            ("Rewrite Review", self.rewrite_review),
            ("Build Prompts", self.build_prompts),
        ]
        for column, (label, callback) in enumerate(buttons):
            button = QPushButton(label)
            button.clicked.connect(callback)
            layout.addWidget(button, 0, column)
            layout.setColumnStretch(column, 1)
        return group

    def new_project(self) -> None:
        title = self.project_panel.project_title() or "Untitled Project"
        self._run_ui_action(
            lambda: self.project_controller.create_project(title),
            "Created project",
        )
        self.refresh_all()

    def open_project(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            "",
            "Project JSON (*.json);;All Files (*)",
        )
        if not path:
            return
        self._run_ui_action(lambda: self.project_controller.open_project(path), "Opened project")
        self.refresh_all()

    def save_project(self) -> None:
        if self.project_controller.project_path is None:
            self.save_project_as()
            return
        self._run_ui_action(lambda: self.project_controller.save_project(), "Saved project")
        self.refresh_project_info()

    def save_project_as(self) -> None:
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Project",
            "",
            "Project JSON (*.json);;All Files (*)",
        )
        if not path:
            return
        self._run_ui_action(lambda: self.project_controller.save_project(path), "Saved project")
        self.refresh_project_info()

    def add_chapter(self) -> None:
        self.project_controller.require_project()
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Add Source Chapter",
            "",
            "Text Files (*.txt);;All Files (*)",
        )
        if not path:
            return
        title, ok = QInputDialog.getText(self, "Chapter Title", "Chapter title")
        if not ok or not title:
            return
        chapter_number, ok = QInputDialog.getInt(
            self,
            "Chapter Number",
            "Chapter number",
            1,
            1,
            9999,
        )
        if not ok:
            return
        self._run_ui_action(
            lambda: self.project_controller.add_chapter_from_file(
                title=title,
                chapter_number=chapter_number,
                text_file=path,
            ),
            "Added chapter",
        )
        self.refresh_all()

    def select_chapter(self, chapter_id: str) -> None:
        self.selected_chapter_id = chapter_id
        chapter = self.project_controller.find_chapter(chapter_id)
        self.source_panel.set_current_chapter(chapter)

    def update_chapter(self, chapter_id: str, values: dict[str, object]) -> None:
        self._run_ui_action(
            lambda: self.project_controller.update_chapter(chapter_id, **values),
            "Updated chapter",
        )
        self.refresh_all()

    def select_episode(self, episode_id: str) -> None:
        self.selected_episode_id = episode_id
        episode = self.generation_controller.find_episode(
            self.project_controller.require_project(),
            episode_id,
        )
        self.browser.set_scenes(episode.scenes)
        self.beat_editor.clear()

    def select_scene(self, scene_id: str) -> None:
        self.selected_scene_id = scene_id
        scene = self._current_scene(scene_id)
        self.browser.set_beats(scene.ordered_beats())
        self.beat_editor.clear()

    def select_beat(self, beat_id: str) -> None:
        self.selected_beat_id = beat_id
        self.beat_editor.set_beat(self._find_beat(beat_id))

    def parse_story(self) -> None:
        chapter_id = self._require_chapter_id()
        settings = self.episode_panel.settings()
        self._run_ui_action(
            lambda: self.generation_controller.parse_story(
                self.project_controller.require_project(),
                chapter_id,
                ai_mode=str(settings["ai_mode"]),
                model=settings["model"],
            ),
            "Parsed story",
        )

    def plan_episode(self) -> None:
        chapter_id = self._require_chapter_id()
        settings = self.episode_panel.settings()
        episode = self._run_ui_action(
            lambda: self.generation_controller.plan_episode(
                self.project_controller.require_project(),
                chapter_id=chapter_id,
                episode_title=str(settings["episode_title"]),
                tone=str(settings["tone"]),
                density=str(settings["density"]),
                ai_mode=str(settings["ai_mode"]),
                model=settings["model"],
            ),
            "Planned episode",
        )
        if episode:
            self.selected_episode_id = episode.episode_id
        self.refresh_all()

    def generate_beats(self) -> None:
        episode_id = self._require_episode_id()
        settings = self.episode_panel.settings()
        self._run_ui_action(
            lambda: self.generation_controller.generate_beats(
                self.project_controller.require_project(),
                episode_id,
                density=str(settings["density"]),
                ai_mode=str(settings["ai_mode"]),
                model=settings["model"],
            ),
            "Generated beats",
        )
        self.refresh_all()

    def rewrite_review(self) -> None:
        episode_id = self._require_episode_id()
        settings = self.episode_panel.settings()
        self._run_ui_action(
            lambda: self.generation_controller.rewrite_review(
                self.project_controller.require_project(),
                episode_id,
                tone=str(settings["tone"]),
                density=str(settings["density"]),
                ai_mode=str(settings["ai_mode"]),
                model=settings["model"],
            ),
            "Rewrote review",
        )
        self.refresh_all()

    def build_prompts(self) -> None:
        episode_id = self._require_episode_id()
        settings = self.episode_panel.settings()
        self._run_ui_action(
            lambda: self.generation_controller.build_prompts(
                self.project_controller.require_project(),
                episode_id,
                style_preset_id=settings["style_preset_id"],
                ai_mode=str(settings["ai_mode"]),
                model=settings["model"],
            ),
            "Built prompts",
        )
        self.refresh_all()

    def run_full_pipeline(self) -> None:
        chapter_id = self._require_chapter_id()
        settings = self.episode_panel.settings()
        episode = self._run_ui_action(
            lambda: self.generation_controller.run_full_pipeline(
                self.project_controller.require_project(),
                chapter_id=chapter_id,
                episode_title=str(settings["episode_title"]),
                tone=str(settings["tone"]),
                density=str(settings["density"]),
                style_preset_id=settings["style_preset_id"],
                ai_mode=str(settings["ai_mode"]),
                model=settings["model"],
            ),
            "Pipeline complete",
        )
        if episode:
            self.selected_episode_id = episode.episode_id
        self.refresh_all()

    def update_beat(self, beat_id: str, values: dict[str, object]) -> None:
        beat = self._find_beat(beat_id)
        self.generation_controller.update_beat_fields(beat, **values)
        self.project_controller.require_project().touch()
        self.set_status("Updated beat")
        self.refresh_all()

    def export_episode(self, export_format: str) -> None:
        episode_id = self._require_episode_id()
        suffix_by_format = {
            "markdown": ".md",
            "json": ".json",
            "csv": ".csv",
            "review-txt": ".txt",
            "prompts-txt": ".txt",
        }
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Episode",
            "",
            f"Output (*{suffix_by_format.get(export_format, '.txt')});;All Files (*)",
        )
        if not path:
            return
        self._run_ui_action(
            lambda: self.export_controller.export_episode(
                self.project_controller.require_project(),
                episode_id,
                export_format=export_format,
                output_path=path,
            ),
            f"Exported {Path(path).name}",
        )

    def export_profile(self, profile_id: str) -> None:
        episode_id = self._require_episode_id()
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Export Profile",
            "",
        )
        if not output_dir:
            return
        paths = self._run_ui_action(
            lambda: self.export_profile_controller.export_episode_with_profile(
                self.project_controller.require_project(),
                episode_id,
                profile_id,
                output_dir,
            ),
            f"Exported profile {profile_id}",
        )
        if paths:
            self.set_status("Created files: " + ", ".join(str(path) for path in paths))

    def refresh_all(self) -> None:
        project = self.project_controller.project
        if project is None:
            return
        self.refresh_project_info()
        self.source_panel.set_chapters(project.source_chapters)
        self.episode_panel.set_episodes(project.review_episodes)
        if self.selected_episode_id:
            try:
                self.select_episode(self.selected_episode_id)
            except LookupError:
                self.selected_episode_id = None
        if self.selected_scene_id and self.selected_episode_id:
            try:
                self.select_scene(self.selected_scene_id)
            except LookupError:
                self.selected_scene_id = None
        if self.selected_beat_id:
            try:
                self.select_beat(self.selected_beat_id)
            except LookupError:
                self.selected_beat_id = None

    def refresh_project_info(self) -> None:
        project = self.project_controller.project
        if project is None:
            return
        path = str(self.project_controller.project_path or "")
        self.project_panel.set_project_info(project.title, path)

    def set_status(self, message: str) -> None:
        self.status_area.appendPlainText(message)

    def _load_export_profiles(self) -> None:
        try:
            self.export_panel.set_profiles(self.export_profile_controller.list_profiles())
        except Exception as exc:
            self.set_status(f"Export profiles unavailable: {exc}")

    def _run_ui_action(self, action: Callable[[], Any], success_message: str):
        try:
            result = action()
        except Exception as exc:
            self.set_status(str(exc))
            QMessageBox.critical(self, "Story Review", str(exc))
            return None
        self.set_status(success_message)
        return result

    def _require_chapter_id(self) -> str:
        chapter_id = self.selected_chapter_id or self.source_panel.selected_chapter_id()
        if not chapter_id:
            raise ValueError("Select a source chapter first.")
        return chapter_id

    def _require_episode_id(self) -> str:
        episode_id = self.selected_episode_id or self.episode_panel.selected_episode_id()
        if not episode_id:
            raise ValueError("Select an episode first.")
        return episode_id

    def _current_scene(self, scene_id: str) -> Scene:
        project = self.project_controller.require_project()
        episode_id = self._require_episode_id()
        return self.generation_controller.find_scene(project, episode_id, scene_id)

    def _find_beat(self, beat_id: str) -> Beat:
        project = self.project_controller.require_project()
        for episode in project.review_episodes:
            for scene in episode.scenes:
                for beat in scene.beats:
                    if beat.beat_id == beat_id:
                        return beat
        raise LookupError(f"Beat not found: {beat_id}")


def create_main_window() -> tuple[QApplication, MainWindow]:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    return app, window
