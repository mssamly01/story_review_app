import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow, create_main_window


class PySideUISmokeTests(unittest.TestCase):
    def test_main_window_can_be_constructed(self) -> None:
        app = QApplication.instance() or QApplication([])
        window = MainWindow()

        self.assertEqual(window.windowTitle(), "Story Review Studio")
        self.assertIsNotNone(window.project_panel)
        self.assertIsNotNone(app)

    def test_create_main_window_returns_app_and_window(self) -> None:
        app, window = create_main_window()

        self.assertIsNotNone(app)
        self.assertIsInstance(window, MainWindow)


if __name__ == "__main__":
    unittest.main()
