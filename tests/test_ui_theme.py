"""Tests for the desktop UI theme loader (``app.ui.theme``).

These tests do not require a display — ``QT_QPA_PLATFORM=offscreen`` is set so
the QSS / QPalette plumbing can be exercised in headless CI.
"""

from __future__ import annotations

import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.theme import (
    Theme,
    apply_theme,
    current_theme,
    load_qss,
    palette_color,
)


def _app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


class ThemeEnumTests(unittest.TestCase):
    def test_from_string_known(self) -> None:
        self.assertEqual(Theme.from_string("dark"), Theme.DARK)
        self.assertEqual(Theme.from_string("LIGHT"), Theme.LIGHT)

    def test_from_string_unknown_falls_back_to_dark(self) -> None:
        self.assertEqual(Theme.from_string("garbage"), Theme.DARK)
        self.assertEqual(Theme.from_string(None), Theme.DARK)
        self.assertEqual(Theme.from_string(""), Theme.DARK)


class QSSLoaderTests(unittest.TestCase):
    def test_dark_qss_loads_with_expected_selectors(self) -> None:
        qss = load_qss(Theme.DARK)
        self.assertTrue(qss, "dark.qss must not be empty")
        for marker in (
            "QListWidget#nav-sidebar",
            "QToolBar#app-header",
            "QListView#beat-grid",
            "QPushButton#primary",
            "QScrollArea#inspector",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, qss)

    def test_light_qss_loads_with_expected_selectors(self) -> None:
        qss = load_qss(Theme.LIGHT)
        self.assertTrue(qss)
        self.assertIn("QListWidget#nav-sidebar", qss)
        self.assertIn("QPushButton#primary", qss)

    def test_qss_does_not_use_unsupported_css_features(self) -> None:
        """Qt's QSS parser silently drops some CSS features; flag obvious ones.

        Note: ``text-transform`` IS supported by Qt's QSS, so we only ban the
        standalone ``transform:`` and ``transition:`` declarations.
        """
        import re

        for theme in (Theme.DARK, Theme.LIGHT):
            qss = load_qss(theme)
            self.assertNotIn("transition:", qss, "QSS does not support `transition`")
            # Match `transform:` only when it's not preceded by a hyphen
            # (so `text-transform:` doesn't trigger).
            self.assertIsNone(
                re.search(r"(?<![-\w])transform:", qss),
                "QSS does not support standalone `transform:`",
            )


class ApplyThemeTests(unittest.TestCase):
    def test_apply_dark_sets_window_palette_and_stylesheet(self) -> None:
        app = _app()
        apply_theme(app, Theme.DARK)
        self.assertEqual(current_theme(), Theme.DARK)
        self.assertIn("QListWidget#nav-sidebar", app.styleSheet())
        # Palette window color should be near-black for dark theme.
        window = app.palette().color(app.palette().ColorRole.Window)
        self.assertLess(window.value(), 80, "dark theme should have dim window bg")

    def test_apply_light_sets_window_palette_and_stylesheet(self) -> None:
        app = _app()
        apply_theme(app, Theme.LIGHT)
        self.assertEqual(current_theme(), Theme.LIGHT)
        self.assertIn("QListWidget#nav-sidebar", app.styleSheet())
        window = app.palette().color(app.palette().ColorRole.Window)
        self.assertGreater(window.value(), 200, "light theme should have bright window bg")

    def test_toggle_round_trip_does_not_crash(self) -> None:
        app = _app()
        for theme in (Theme.DARK, Theme.LIGHT, Theme.DARK, Theme.LIGHT):
            apply_theme(app, theme)
            self.assertEqual(current_theme(), theme)


class PaletteTokenTests(unittest.TestCase):
    REQUIRED_TOKENS = (
        "card_bg",
        "card_bg_hover",
        "card_border",
        "card_border_selected",
        "thumbnail_bg",
        "accent",
        "muted_text",
        "status_planned",
        "status_has_text",
        "status_has_prompt",
        "status_approved",
        "text",
        "highlighted_text",
    )

    def test_all_tokens_resolve_for_both_themes(self) -> None:
        for theme in (Theme.DARK, Theme.LIGHT):
            for token in self.REQUIRED_TOKENS:
                with self.subTest(theme=theme, token=token):
                    color = palette_color(theme, token)
                    self.assertTrue(color.isValid())
                    # Sentinel magenta would indicate a missing token.
                    self.assertNotEqual((color.red(), color.green(), color.blue()), (255, 0, 255))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
