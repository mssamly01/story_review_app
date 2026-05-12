"""StoryFlow-like sidebar navigation with a ``QTabWidget``-style API.

The app keeps a tiny subset of ``QTabWidget``'s API so existing callers and UI
tests continue to work. Visually, this widget presents the workflow as a simple
ordered left rail, closer to the reference StoryFlow experience.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class SidebarTabWidget(QWidget):
    """A drop-in replacement for ``QTabWidget`` with vertical navigation."""

    currentChanged = Signal(int)

    SIDEBAR_WIDTH = 268
    TAB_DESCRIPTIONS = {
        "Dá»± Ã¡n & Nguá»“n": "Nháº­p truyá»‡n vÃ  quáº£n lÃ½ project",
        "Bible / Style": "NhÃ¢n váº­t, bá»‘i cáº£nh, phong cÃ¡ch",
        "Káº¿ hoáº¡ch táº­p": "Scene, beat, review text",
        "Beat Studio": "Sá»­a beat vÃ  prompt áº£nh",
        "Xem Beat": "Duyá»‡t ná»™i dung theo beat",
        "Cháº¥t lÆ°á»£ng": "Kiá»ƒm tra vÃ  gá»£i Ã½ sá»­a",
        "CÃ i Ä‘áº·t": "AI mode vÃ  tuá»³ chá»n",
    }
    DEFAULT_DESCRIPTIONS = [
        "Nhập truyện và quản lý project",
        "Nhân vật, bối cảnh, phong cách",
        "Scene, beat, review text",
        "Sửa beat và prompt ảnh",
        "Duyệt nội dung theo beat",
        "Kiểm tra và gợi ý sửa",
        "AI mode và tuỳ chọn",
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("storyflow-shell")
        self._labels: list[str] = []

        self.nav_frame = QFrame(self)
        self.nav_frame.setObjectName("storyflow-sidebar")
        self.nav_frame.setFixedWidth(self.SIDEBAR_WIDTH)

        nav_layout = QVBoxLayout(self.nav_frame)
        nav_layout.setContentsMargins(18, 18, 18, 18)
        nav_layout.setSpacing(12)

        self.brand_label = QLabel("StoryFlow Review", self.nav_frame)
        self.brand_label.setObjectName("storyflow-brand")
        nav_layout.addWidget(self.brand_label)

        self.tagline_label = QLabel("Review narration + image prompts", self.nav_frame)
        self.tagline_label.setObjectName("storyflow-tagline")
        nav_layout.addWidget(self.tagline_label)

        self.workflow_label = QLabel("WORKFLOW", self.nav_frame)
        self.workflow_label.setObjectName("storyflow-nav-heading")
        nav_layout.addWidget(self.workflow_label)

        self.sidebar = QListWidget(self.nav_frame)
        self.sidebar.setObjectName("nav-sidebar")
        self.sidebar.setFrameShape(QListWidget.Shape.NoFrame)
        self.sidebar.setIconSize(QSize(20, 20))
        self.sidebar.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        nav_layout.addWidget(self.sidebar, 1)

        self.stack = QStackedWidget(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.nav_frame)
        layout.addWidget(self.stack, 1)

        self.sidebar.currentRowChanged.connect(self._on_sidebar_changed)

    def addTab(self, widget: QWidget, label: str) -> int:
        """Append a tab and return the new tab index."""
        index = len(self._labels)
        self._labels.append(label)
        description = self.TAB_DESCRIPTIONS.get(label, "")
        if not description and index < len(self.DEFAULT_DESCRIPTIONS):
            description = self.DEFAULT_DESCRIPTIONS[index]
        display_label = f"{index + 1:02d}  {label}"
        if description:
            display_label = f"{display_label}\n{description}"
        item = QListWidgetItem(display_label)
        item.setData(Qt.ItemDataRole.UserRole, label)
        item.setSizeHint(QSize(self.SIDEBAR_WIDTH - 36, 60))
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

    def _on_sidebar_changed(self, row: int) -> None:
        if row < 0:
            return
        self.stack.setCurrentIndex(row)
        self.currentChanged.emit(row)
