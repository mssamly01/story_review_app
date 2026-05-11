"""Theme loader for the Story Review Studio desktop UI.

Two themes ship out of the box: a dark theme (default) inspired by Storyboard
Pro / Boords, and a light theme. Each is a single QSS file under
``app/ui/qss/`` that uses ``objectName`` selectors set on specific widgets in
the Python code to stay narrow and readable.

The user's last choice is persisted via ``QSettings`` so the app remembers
the theme between launches.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QPalette

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication


_QSS_DIR = Path(__file__).parent / "qss"
_SETTINGS_ORG = "mssamly01"
_SETTINGS_APP = "story_review_studio"
_SETTINGS_KEY = "ui/theme"


class Theme(Enum):
    """Available UI themes. Add new entries when shipping more QSS files."""

    DARK = "dark"
    LIGHT = "light"

    @classmethod
    def from_string(cls, value: str | None) -> "Theme":
        if not value:
            return cls.DARK
        try:
            return cls(value.lower())
        except ValueError:
            return cls.DARK


# Palette tokens — kept in sync with the QSS files so widgets that can't be
# styled purely via QSS (e.g. QScrollArea internals, QPalette-driven custom
# painters) still match the rest of the UI.
_PALETTES: dict[Theme, dict[str, str]] = {
    Theme.DARK: {
        "window": "#0f1115",
        "window_text": "#e6e8ee",
        "base": "#0f1115",
        "alternate_base": "#12151b",
        "text": "#e6e8ee",
        "button": "#1f232c",
        "button_text": "#e6e8ee",
        "bright_text": "#ffffff",
        "highlight": "#5b8def",
        "highlighted_text": "#ffffff",
        "tooltip_base": "#14171e",
        "tooltip_text": "#e6e8ee",
        "placeholder_text": "#5b6472",
    },
    Theme.LIGHT: {
        "window": "#fafbfc",
        "window_text": "#1a1d23",
        "base": "#ffffff",
        "alternate_base": "#f9fafb",
        "text": "#1a1d23",
        "button": "#ffffff",
        "button_text": "#1a1d23",
        "bright_text": "#000000",
        "highlight": "#2b6cff",
        "highlighted_text": "#ffffff",
        "tooltip_base": "#ffffff",
        "tooltip_text": "#1a1d23",
        "placeholder_text": "#9aa0a6",
    },
}


def _qss_path(theme: Theme) -> Path:
    return _QSS_DIR / f"{theme.value}.qss"


def load_qss(theme: Theme) -> str:
    """Read the QSS file for ``theme``. Returns empty string if not found."""
    path = _qss_path(theme)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _build_palette(theme: Theme) -> QPalette:
    tokens = _PALETTES[theme]
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(tokens["window"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(tokens["window_text"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(tokens["base"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(tokens["alternate_base"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(tokens["text"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(tokens["button"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(tokens["button_text"]))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(tokens["bright_text"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(tokens["highlight"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(tokens["highlighted_text"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(tokens["tooltip_base"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(tokens["tooltip_text"]))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(tokens["placeholder_text"]))
    return palette


def apply_theme(app: QApplication, theme: Theme) -> None:
    """Apply ``theme`` to the running application (palette + QSS)."""
    app.setPalette(_build_palette(theme))
    qss = load_qss(theme)
    app.setStyleSheet(qss)
    set_current_theme(theme)


def _settings() -> QSettings:
    return QSettings(_SETTINGS_ORG, _SETTINGS_APP)


def load_persisted_theme() -> Theme:
    """Return the user's last chosen theme, defaulting to dark."""
    return Theme.from_string(_settings().value(_SETTINGS_KEY, Theme.DARK.value, type=str))


def save_persisted_theme(theme: Theme) -> None:
    """Persist ``theme`` so the next launch uses the same choice."""
    _settings().setValue(_SETTINGS_KEY, theme.value)


def palette_color(theme: Theme, token: str) -> QColor:
    """Look up a palette token used by custom painters (e.g. card delegates).

    Tokens match the keys in the internal ``_PALETTES`` dict plus a few extras
    that are convenient for delegates:

    * ``card_bg`` / ``card_bg_hover`` / ``card_border`` / ``card_border_selected``
    * ``thumbnail_bg``
    * ``accent`` / ``muted_text``
    """
    extras: dict[Theme, dict[str, str]] = {
        Theme.DARK: {
            "card_bg": "#14171e",
            "card_bg_hover": "#1a1d25",
            "card_border": "#2a2f3a",
            "card_border_selected": "#5b8def",
            "thumbnail_bg": "#0a0c10",
            "accent": "#5b8def",
            "muted_text": "#8a93a6",
            "status_planned": "#5b6472",
            "status_has_text": "#e8a14d",
            "status_has_prompt": "#5b8def",
            "status_approved": "#2bb673",
        },
        Theme.LIGHT: {
            "card_bg": "#ffffff",
            "card_bg_hover": "#f6f8fa",
            "card_border": "#e3e7ec",
            "card_border_selected": "#2b6cff",
            "thumbnail_bg": "#f1f3f5",
            "accent": "#2b6cff",
            "muted_text": "#6b7280",
            "status_planned": "#9aa0a6",
            "status_has_text": "#c47f1f",
            "status_has_prompt": "#2b6cff",
            "status_approved": "#1f9d57",
        },
    }
    table = {**_PALETTES[theme], **extras[theme]}
    return QColor(table.get(token, "#ff00ff"))


_CURRENT_THEME: Theme = Theme.DARK


def current_theme() -> Theme:
    """Return the theme that was last applied via :func:`apply_theme`."""
    return _CURRENT_THEME


def set_current_theme(theme: Theme) -> None:
    """Record that ``theme`` is now active; used by :func:`apply_theme` and
    by tests that exercise palette lookups without a running QApplication."""
    global _CURRENT_THEME
    _CURRENT_THEME = theme
