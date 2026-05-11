import importlib
import os
from unittest.mock import patch
import unittest


class UISmokeTests(unittest.TestCase):
    def test_main_window_can_be_imported(self) -> None:
        module = importlib.import_module("app.ui.main_window")

        self.assertTrue(hasattr(module, "MainWindow"))

    def test_ui_import_needs_no_credentials(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            modules = [
                "app.ui.main_window",
                "app.ui.app_state",
                "app.ui.project_tab",
                "app.ui.source_tab",
                "app.ui.episode_planner_tab",
                "app.ui.beat_studio_tab",
                "app.ui.bible_style_tab",
                "app.ui.quality_repair_tab",
                "app.ui.export_tab",
                "app.ui.app_runner",
                # Legacy panels:
                "app.ui.project_panel",
                "app.ui.source_chapter_panel",
                "app.ui.episode_panel",
                "app.ui.beat_browser",
                "app.ui.beat_editor",
                "app.ui.export_panel",
            ]
            for module_name in modules:
                with self.subTest(module_name=module_name):
                    module = importlib.import_module(module_name)
                    self.assertIsNotNone(module)


if __name__ == "__main__":
    unittest.main()

