"""Tests for the redesigned Beat Studio panel grid view."""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QModelIndex, QRect
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QListWidgetItem,
    QPlainTextEdit,
    QStyleOptionViewItem,
)

from app.domain.beat import Beat
from app.domain.episode import ReviewEpisode
from app.domain.project import Project
from app.domain.scene import Scene
from app.services.project_service import ProjectService
from app.ui.beat_card_delegate import (
    CARD_DATA_ROLE,
    CARD_HEIGHT,
    CARD_WIDTH,
    BeatCardData,
    BeatCardDelegate,
)
from app.ui.main_window import MainWindow


def _app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


def _make_project() -> Project:
    project = ProjectService().create_project("Demo project")

    scene = Scene(scene_id="sc1", episode_id="ep1", title="Scene 1")
    scene.beats.extend(
        [
            Beat(
                beat_id="b1",
                scene_id="sc1",
                order_index=1,
                story_function="opening",
                review_text="Mở đầu — gia đình về thăm căn nhà cũ.",
                image_prompt="dark mansion at dusk",
                action="",
            ),
            Beat(
                beat_id="b2",
                scene_id="sc1",
                order_index=2,
                story_function="rising",
                review_text="Mẹ phát hiện căn phòng bị khoá.",
                action="",
            ),
        ]
    )

    episode = ReviewEpisode(episode_id="ep1", title="Tập 1", summary="")
    episode.scenes.append(scene)
    project.review_episodes.append(episode)
    return project


def _make_studio_with_project(window: MainWindow) -> None:
    project = _make_project()
    window.project_controller.project = project
    window.app_state.project = project
    window.app_state.selected_episode_id = "ep1"
    window.app_state.selected_scene_id = "sc1"
    window.studio_tab.refresh()


class ViewModeToggleTests(unittest.TestCase):
    def setUp(self) -> None:
        _app()
        self.window = MainWindow()

    def test_default_view_mode_is_grid(self) -> None:
        self.assertEqual(self.window.studio_tab.view_mode, "grid")
        self.assertTrue(self.window.studio_tab.btn_view_grid.isChecked())
        self.assertFalse(self.window.studio_tab.btn_view_table.isChecked())
        self.assertEqual(self.window.studio_tab.beats_stack.currentIndex(), 0)

    def test_switch_to_table_mode(self) -> None:
        self.window.studio_tab.set_view_mode("table")
        self.assertEqual(self.window.studio_tab.view_mode, "table")
        self.assertFalse(self.window.studio_tab.btn_view_grid.isChecked())
        self.assertTrue(self.window.studio_tab.btn_view_table.isChecked())
        self.assertEqual(self.window.studio_tab.beats_stack.currentIndex(), 1)

    def test_switch_back_to_grid_mode(self) -> None:
        self.window.studio_tab.set_view_mode("table")
        self.window.studio_tab.set_view_mode("grid")
        self.assertEqual(self.window.studio_tab.view_mode, "grid")
        self.assertEqual(self.window.studio_tab.beats_stack.currentIndex(), 0)

    def test_invalid_view_mode_is_ignored(self) -> None:
        self.window.studio_tab.set_view_mode("kanban")
        self.assertEqual(self.window.studio_tab.view_mode, "grid")


class GridPopulationTests(unittest.TestCase):
    def setUp(self) -> None:
        _app()
        self.window = MainWindow()
        _make_studio_with_project(self.window)

    def test_grid_and_table_have_the_same_number_of_rows(self) -> None:
        studio = self.window.studio_tab
        self.assertEqual(studio.beat_grid.count(), 2)
        self.assertEqual(studio.beat_table.rowCount(), 2)

    def test_grid_items_carry_card_data(self) -> None:
        studio = self.window.studio_tab
        for i in range(studio.beat_grid.count()):
            item = studio.beat_grid.item(i)
            payload = item.data(CARD_DATA_ROLE)
            self.assertIsInstance(payload, BeatCardData)
            self.assertTrue(payload.beat_id.startswith("b"))

    def test_selecting_a_grid_item_loads_inspector_fields(self) -> None:
        studio = self.window.studio_tab
        studio.beat_grid.setCurrentRow(0)
        QApplication.processEvents()
        self.assertEqual(self.window.app_state.selected_beat_id, "b1")
        # review_text field is a QPlainTextEdit; verify it loaded the beat text.
        widget = studio.fields["review_text"]
        self.assertIsInstance(widget, QPlainTextEdit)
        self.assertIn("Mở đầu", widget.toPlainText())


class InspectorGroupsTests(unittest.TestCase):
    def setUp(self) -> None:
        _app()
        self.window = MainWindow()

    def test_inspector_groups_cover_all_fields(self) -> None:
        studio = self.window.studio_tab
        grouped = {f for _, fs in studio.FIELD_GROUPS for f in fs}
        self.assertEqual(grouped, set(studio.FIELD_NAMES))

    def test_inspector_has_three_named_groups(self) -> None:
        names = [name for name, _ in self.window.studio_tab.FIELD_GROUPS]
        self.assertEqual(names, ["Narration", "Prompt", "Context"])


class BeatCardDelegateTests(unittest.TestCase):
    def setUp(self) -> None:
        _app()
        self.delegate = BeatCardDelegate()

    def _opt(self) -> QStyleOptionViewItem:
        opt = QStyleOptionViewItem()
        opt.rect = QRect(0, 0, CARD_WIDTH, CARD_HEIGHT)
        return opt

    def test_size_hint_is_card_dimensions(self) -> None:
        opt = self._opt()
        idx = QModelIndex()
        size = self.delegate.sizeHint(opt, idx)
        self.assertEqual(size.width(), CARD_WIDTH)
        self.assertEqual(size.height(), CARD_HEIGHT)

    def test_paint_handles_missing_card_data_gracefully(self) -> None:
        """Painting a row without a BeatCardData payload must not raise."""
        pixmap = QPixmap(CARD_WIDTH, CARD_HEIGHT)
        pixmap.fill()
        painter = QPainter(pixmap)
        try:
            self.delegate.paint(painter, self._opt(), QModelIndex())
        finally:
            painter.end()

    def test_paint_renders_when_image_is_missing(self) -> None:
        """A card with ``image_path=None`` should still paint a placeholder."""
        from app.ui.beat_studio_tab import _build_card_data

        beat = Beat(
            beat_id="b1",
            scene_id="sc1",
            order_index=1,
            story_function="opening",
            review_text="Hello world",
        )
        data = _build_card_data(beat)

        item = QListWidgetItem()
        item.setData(CARD_DATA_ROLE, data)

        # Stand-in QModelIndex via a tiny QListWidget so the delegate can
        # actually read its data.
        from PySide6.QtWidgets import QListWidget

        listw = QListWidget()
        listw.addItem(item)
        index = listw.indexFromItem(item)

        pixmap = QPixmap(CARD_WIDTH, CARD_HEIGHT)
        pixmap.fill()
        painter = QPainter(pixmap)
        try:
            self.delegate.paint(painter, self._opt(), index)
        finally:
            painter.end()

    def test_card_data_status_dots_reflect_state(self) -> None:
        from app.ui.beat_studio_tab import _build_card_data

        beat = Beat(
            beat_id="b1",
            scene_id="sc1",
            order_index=1,
            story_function="opening",
            review_text="filled",
            image_prompt="filled prompt",
        )
        data = _build_card_data(beat)
        self.assertTrue(data.has_review_text)
        self.assertTrue(data.has_image_prompt)
        self.assertFalse(data.has_image)
        self.assertEqual(data.status_dots[1], "has_text")
        self.assertEqual(data.status_dots[2], "has_prompt")


class ThemeWiredIntoMainWindowTests(unittest.TestCase):
    def setUp(self) -> None:
        _app()

    def test_main_window_creates_view_menu_with_themes(self) -> None:
        window = MainWindow()
        menus = [a.text() for a in window.menuBar().actions()]
        self.assertIn("&View", menus)

    def test_toggle_theme_button_changes_current_theme(self) -> None:
        from app.ui.theme import Theme, apply_theme, current_theme

        apply_theme(_app(), Theme.DARK)
        window = MainWindow()
        with patch("app.ui.main_window.save_persisted_theme"):
            window._toggle_theme()
        self.assertEqual(current_theme(), Theme.LIGHT)
        with patch("app.ui.main_window.save_persisted_theme"):
            window._toggle_theme()
        self.assertEqual(current_theme(), Theme.DARK)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
