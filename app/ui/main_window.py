"""Main Tkinter window for the minimal desktop UI."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from app.controllers.export_controller import ExportController
from app.controllers.generation_controller import GenerationController
from app.controllers.project_controller import ProjectController
from app.domain.beat import Beat
from app.domain.episode import ReviewEpisode
from app.domain.scene import Scene
from app.ui.beat_browser import BeatBrowser
from app.ui.beat_editor import BeatEditor
from app.ui.episode_panel import EpisodePanel
from app.ui.export_panel import ExportPanel
from app.ui.project_panel import ProjectPanel
from app.ui.source_chapter_panel import SourceChapterPanel


class MainWindow(ttk.Frame):
    def __init__(
        self,
        master: tk.Tk,
        project_controller: ProjectController | None = None,
        generation_controller: GenerationController | None = None,
        export_controller: ExportController | None = None,
    ) -> None:
        super().__init__(master)
        self.master = master
        self.project_controller = project_controller or ProjectController()
        self.generation_controller = generation_controller or GenerationController(
            self.project_controller.project_service
        )
        self.export_controller = export_controller or ExportController(
            self.project_controller.project_service
        )
        self.selected_chapter_id: str | None = None
        self.selected_episode_id: str | None = None
        self.selected_scene_id: str | None = None
        self.selected_beat_id: str | None = None
        self.status_var = tk.StringVar(value="Ready")

        self.master.title("Story Review Studio")
        self.pack(fill="both", expand=True)
        self._build_layout()

    def _build_layout(self) -> None:
        self.project_panel = ProjectPanel(
            self,
            {
                "new_project": self.new_project,
                "open_project": self.open_project,
                "save_project": self.save_project,
                "save_project_as": self.save_project_as,
            },
        )
        self.project_panel.grid(row=0, column=0, columnspan=3, sticky="ew", padx=6, pady=4)

        self.source_panel = SourceChapterPanel(
            self,
            {
                "add_chapter": self.add_chapter,
                "select_chapter": self.select_chapter,
                "update_chapter": self.update_chapter,
            },
        )
        self.source_panel.grid(row=1, column=0, sticky="nsew", padx=6, pady=4)

        self.episode_panel = EpisodePanel(
            self,
            {
                "plan_episode": self.plan_episode,
                "run_pipeline": self.run_full_pipeline,
                "select_episode": self.select_episode,
            },
        )
        self.episode_panel.grid(row=1, column=1, sticky="nsew", padx=6, pady=4)

        self.browser = BeatBrowser(
            self,
            {
                "select_scene": self.select_scene,
                "select_beat": self.select_beat,
            },
        )
        self.browser.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=6, pady=4)

        self.beat_editor = BeatEditor(
            self,
            {
                "update_beat": self.update_beat,
            },
        )
        self.beat_editor.grid(row=1, column=2, rowspan=2, sticky="nsew", padx=6, pady=4)

        actions = ttk.LabelFrame(self, text="Pipeline")
        actions.grid(row=3, column=0, columnspan=2, sticky="ew", padx=6, pady=4)
        ttk.Button(actions, text="Parse Story", command=self.parse_story).grid(
            row=0, column=0, sticky="ew", padx=2
        )
        ttk.Button(actions, text="Generate Beats", command=self.generate_beats).grid(
            row=0, column=1, sticky="ew", padx=2
        )
        ttk.Button(actions, text="Rewrite Review", command=self.rewrite_review).grid(
            row=0, column=2, sticky="ew", padx=2
        )
        ttk.Button(actions, text="Build Prompts", command=self.build_prompts).grid(
            row=0, column=3, sticky="ew", padx=2
        )
        for column in range(4):
            actions.columnconfigure(column, weight=1)

        self.export_panel = ExportPanel(
            self,
            {
                "export_episode": self.export_episode,
            },
        )
        self.export_panel.grid(row=3, column=2, sticky="ew", padx=6, pady=4)

        ttk.Label(self, textvariable=self.status_var).grid(
            row=4, column=0, columnspan=3, sticky="ew", padx=6, pady=4
        )
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)

    def new_project(self) -> None:
        self._run_ui_action(
            lambda: self.project_controller.create_project(
                self.project_panel.title_var.get() or "Untitled Project"
            ),
            "Created project",
        )
        self.refresh_all()

    def open_project(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Project JSON", "*.json")])
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
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Project JSON", "*.json")],
        )
        if not path:
            return
        self._run_ui_action(lambda: self.project_controller.save_project(path), "Saved project")
        self.refresh_project_info()

    def add_chapter(self) -> None:
        project = self.project_controller.require_project()
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        title = simpledialog.askstring("Chapter title", "Chapter title")
        if not title:
            return
        chapter_number = simpledialog.askinteger("Chapter number", "Chapter number", minvalue=1)
        if chapter_number is None:
            return
        self._run_ui_action(
            lambda: self.project_controller.add_chapter_from_file(
                title=title,
                chapter_number=chapter_number,
                text_file=path,
            ),
            "Added chapter",
        )
        self.refresh_all(project)

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

    def select_scene(self, scene_id: str) -> None:
        self.selected_scene_id = scene_id
        scene = self._current_scene(scene_id)
        self.browser.set_beats(scene.ordered_beats())

    def select_beat(self, beat_id: str) -> None:
        self.selected_beat_id = beat_id
        beat = self._find_beat(beat_id)
        self.beat_editor.set_beat(beat)

    def parse_story(self) -> None:
        chapter_id = self._require_chapter_id()
        settings = self.episode_panel.settings()
        self._run_ui_action(
            lambda: self.generation_controller.parse_story(
                self.project_controller.require_project(),
                chapter_id,
                ai_mode=settings["ai_mode"],
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
                episode_title=settings["episode_title"],
                tone=settings["tone"],
                density=settings["density"],
                ai_mode=settings["ai_mode"],
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
                density=settings["density"],
                ai_mode=settings["ai_mode"],
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
                tone=settings["tone"],
                density=settings["density"],
                ai_mode=settings["ai_mode"],
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
                ai_mode=settings["ai_mode"],
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
                episode_title=settings["episode_title"],
                tone=settings["tone"],
                density=settings["density"],
                ai_mode=settings["ai_mode"],
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
        path = filedialog.asksaveasfilename(
            defaultextension=suffix_by_format.get(export_format, ".txt")
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

    def refresh_all(self, project=None) -> None:
        project = project or self.project_controller.project
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

    def refresh_project_info(self) -> None:
        project = self.project_controller.project
        if project is None:
            return
        path = str(self.project_controller.project_path or "")
        self.project_panel.set_project_info(project.title, path)

    def set_status(self, message: str) -> None:
        self.status_var.set(message)

    def _run_ui_action(self, action, success_message: str):
        try:
            result = action()
        except Exception as exc:
            self.set_status(str(exc))
            messagebox.showerror("Story Review", str(exc))
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


def create_main_window() -> tuple[tk.Tk, MainWindow]:
    root = tk.Tk()
    return root, MainWindow(root)

