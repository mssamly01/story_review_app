import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.theme import Theme


app = QApplication.instance() or QApplication(sys.argv)


def test_sidebar_uses_storyflow_like_branding():
    window = MainWindow()

    assert window.tabs.brand_label.text() == "StoryFlow Review"
    assert "Review narration" in window.tabs.tagline_label.text()
    assert window.tabs.sidebar.count() == window.tabs.count()


def test_sidebar_items_show_order_and_descriptions_without_changing_tab_api():
    window = MainWindow()

    first_item_text = window.tabs.sidebar.item(0).text()
    assert first_item_text.startswith("01  ")
    assert "\n" in first_item_text
    assert window.tabs.tabText(0) in first_item_text
    assert window.tabs.tabText(0) != first_item_text


def test_main_header_tracks_current_workflow_step():
    window = MainWindow()

    window.tabs.setCurrentIndex(2)

    assert "3 / 7" in window._step_chip.text()


def test_default_theme_is_simple_light_shell():
    assert Theme.from_string(None) == Theme.LIGHT
