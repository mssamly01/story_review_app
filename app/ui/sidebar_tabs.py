"""Vertical sidebar navigation that mimics ``QTabWidget``'s public API.

We use a ``QListWidget`` on the left and a ``QStackedWidget`` on the right
rather than ``QTabWidget`` with ``TabPosition::West`` because the latter
rotates the tab text 90°, which looks bad with Vietnamese labels.

The exposed methods (``addTab``, ``widget``, ``count``, ``tabText``,
``currentIndex``, ``setCurrentIndex``) and the ``currentChanged`` signal are
a strict subset of ``QTabWidget``'s API so the existing UI smoke tests keep
working without modification.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QWidget,
)


class SidebarTabWidget(QWidget):
    """A drop-in replacement for ``QTabWidget`` with vertical navigation."""

    currentChanged = Signal(int)

    SIDEBAR_WIDTH = 200

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._labels: list[str] = []

        self.sidebar = QListWidget(self)
        self.sidebar.setObjectName("nav-sidebar")
        self.sidebar.setFixedWidth(self.SIDEBAR_WIDTH)
        self.sidebar.setFrameShape(QListWidget.Shape.NoFrame)
        self.sidebar.setIconSize(QSize(20, 20))
        self.sidebar.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.stack = QStackedWidget(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack, 1)

        self.sidebar.currentRowChanged.connect(self._on_sidebar_changed)

    # ------- QTabWidget-compatible API -------------------------------------------------
    def addTab(self, widget: QWidget, label: str) -> int:
        """Append a tab; returns the new tab's index."""
        index = len(self._labels)
        self._labels.append(label)
        item = QListWidgetItem(label)
        item.setSizeHint(QSize(self.SIDEBAR_WIDTH, 42))
        self.sidebar.addItem(item)
        self.stack.addWidget(widget)
        if index == 0:
            self.sidebar.setCurrentRow(0)
        return index

    def widget(self, index: int) -> QWidget | None:
        return self.stack.widget(index)

    def count(self) -> int:
        return self.stack.count()

    def tabText(self, index: int) -> str:
        if 0 <= index < len(self._labels):
            return self._labels[index]
        return ""

    def currentIndex(self) -> int:
        return self.stack.currentIndex()

    def setCurrentIndex(self, index: int) -> None:
        if 0 <= index < self.stack.count():
            self.sidebar.setCurrentRow(index)

    # ------- Internals ----------------------------------------------------------------
    def _on_sidebar_changed(self, row: int) -> None:
        if row < 0:
            return
        self.stack.setCurrentIndex(row)
        self.currentChanged.emit(row)
