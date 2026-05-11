"""Custom ``QStyledItemDelegate`` that paints each beat as a Boords-style card.

Cards have three regions:

* a 16:9 thumbnail filled by ``beat.selected_image.image_path`` (placeholder
  text when the beat has no rendered image yet),
* a beat-number chip + status dots,
* a 2-line review/synopsis preview.

The delegate reads its data from a ``QListWidgetItem`` whose ``Qt.UserRole``
holds a :class:`BeatCardData` instance.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QRect, QSize, Qt
from PySide6.QtGui import QFont, QFontMetrics, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

from app.ui.theme import Theme, current_theme, palette_color

CARD_WIDTH = 240
CARD_HEIGHT = 220
THUMB_HEIGHT = 135  # ~16:9 inside a 240px-wide card
CARD_PADDING = 10
CARD_MARGIN = 6

CARD_DATA_ROLE = Qt.ItemDataRole.UserRole + 1


@dataclass(frozen=True)
class BeatCardData:
    """Lightweight payload stored on each grid item.

    Keeping this immutable + flat means the delegate never reaches back into
    the domain model on the paint thread; the grid view refreshes by rebuilding
    its items from scratch.
    """

    beat_id: str
    order_index: int
    review_preview: str
    image_path: str | None
    has_review_text: bool
    has_image_prompt: bool
    has_image: bool
    approved: bool

    @property
    def status_dots(self) -> list[str]:
        """One token per status pip, in display order."""
        return [
            "planned",  # always present so the row is visually balanced
            "has_text" if self.has_review_text else "planned",
            "has_prompt" if self.has_image_prompt else "planned",
            "approved" if self.approved else "planned",
        ]


class BeatCardDelegate(QStyledItemDelegate):
    """Paints :class:`BeatCardData` as a card."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._pixmap_cache: dict[str, QPixmap] = {}

    # ------- Sizing ------------------------------------------------------------------
    def sizeHint(
        self,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> QSize:
        return QSize(CARD_WIDTH, CARD_HEIGHT)

    # ------- Painting ----------------------------------------------------------------
    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> None:
        data = index.data(CARD_DATA_ROLE)
        if not isinstance(data, BeatCardData):
            super().paint(painter, option, index)
            return

        theme = current_theme()
        rect = option.rect.adjusted(CARD_MARGIN, CARD_MARGIN, -CARD_MARGIN, -CARD_MARGIN)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)
        is_hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

        bg_token = "card_bg_hover" if (is_hovered and not is_selected) else "card_bg"
        border_token = "card_border_selected" if is_selected else "card_border"

        painter.setPen(QPen(palette_color(theme, border_token), 1.5 if is_selected else 1.0))
        painter.setBrush(palette_color(theme, bg_token))
        painter.drawRoundedRect(rect, 8, 8)

        # Thumbnail region (inset slightly from the card)
        thumb_rect = QRect(
            rect.left() + CARD_PADDING,
            rect.top() + CARD_PADDING,
            rect.width() - 2 * CARD_PADDING,
            THUMB_HEIGHT,
        )
        self._paint_thumbnail(painter, thumb_rect, data, theme)

        # Beat-number chip + status dots
        chip_rect = QRect(
            thumb_rect.left(),
            thumb_rect.bottom() + 10,
            rect.width() - 2 * CARD_PADDING,
            20,
        )
        self._paint_chip_row(painter, chip_rect, data, theme)

        # Review text preview (2 lines, ellipsised)
        text_rect = QRect(
            thumb_rect.left(),
            chip_rect.bottom() + 6,
            rect.width() - 2 * CARD_PADDING,
            rect.bottom() - chip_rect.bottom() - 8 - CARD_PADDING,
        )
        self._paint_preview_text(painter, text_rect, data.review_preview, theme)

        painter.restore()

    # ------- Pieces -------------------------------------------------------------------
    def _paint_thumbnail(
        self,
        painter: QPainter,
        rect: QRect,
        data: BeatCardData,
        theme: Theme,
    ) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(palette_color(theme, "thumbnail_bg"))
        painter.drawRoundedRect(rect, 6, 6)

        pixmap = self._load_pixmap(data.image_path) if data.image_path else None
        if pixmap is not None and not pixmap.isNull():
            scaled = pixmap.scaled(
                rect.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = rect.left() + (rect.width() - scaled.width()) // 2
            y = rect.top() + (rect.height() - scaled.height()) // 2
            painter.save()
            painter.setClipRect(rect)
            painter.drawPixmap(x, y, scaled)
            painter.restore()
        else:
            placeholder_font = QFont(painter.font())
            placeholder_font.setPointSize(max(9, placeholder_font.pointSize() - 1))
            painter.setFont(placeholder_font)
            painter.setPen(QPen(palette_color(theme, "muted_text")))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Chưa có ảnh")

    def _paint_chip_row(
        self,
        painter: QPainter,
        rect: QRect,
        data: BeatCardData,
        theme: Theme,
    ) -> None:
        # Beat number chip on the left
        chip_text = f"#{data.order_index:03d}"
        chip_font = QFont(painter.font())
        chip_font.setBold(True)
        chip_font.setPointSize(max(9, chip_font.pointSize() - 1))
        painter.setFont(chip_font)
        fm = QFontMetrics(chip_font)
        chip_w = fm.horizontalAdvance(chip_text) + 16
        chip_rect = QRect(rect.left(), rect.top(), chip_w, rect.height())

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(palette_color(theme, "accent"))
        painter.drawRoundedRect(chip_rect, 10, 10)
        painter.setPen(QPen(palette_color(theme, "highlighted_text")))
        painter.drawText(chip_rect, Qt.AlignmentFlag.AlignCenter, chip_text)

        # Status dots on the right
        dot_diameter = 8
        dot_gap = 4
        dots = data.status_dots
        total_w = len(dots) * dot_diameter + (len(dots) - 1) * dot_gap
        start_x = rect.right() - total_w
        y = rect.top() + (rect.height() - dot_diameter) // 2
        painter.setPen(Qt.PenStyle.NoPen)
        for i, status in enumerate(dots):
            token = {
                "planned": "status_planned",
                "has_text": "status_has_text",
                "has_prompt": "status_has_prompt",
                "approved": "status_approved",
            }[status]
            painter.setBrush(palette_color(theme, token))
            painter.drawEllipse(
                start_x + i * (dot_diameter + dot_gap), y, dot_diameter, dot_diameter
            )

    def _paint_preview_text(
        self,
        painter: QPainter,
        rect: QRect,
        text: str,
        theme: Theme,
    ) -> None:
        if not text:
            text = "(chưa có nội dung review)"
        text_font = QFont(painter.font())
        text_font.setBold(False)
        painter.setFont(text_font)
        painter.setPen(QPen(palette_color(theme, "text")))
        flags = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap
        elided = self._elide_to_two_lines(text, text_font, rect.width())
        painter.drawText(rect, int(flags), elided)

    # ------- Helpers ------------------------------------------------------------------
    def _elide_to_two_lines(self, text: str, font: QFont, max_width: int) -> str:
        """Truncate ``text`` to fit visually in roughly two lines."""
        fm = QFontMetrics(font)
        avg_char = max(1, fm.averageCharWidth())
        chars_per_line = max(8, max_width // avg_char)
        budget = chars_per_line * 2
        if len(text) <= budget:
            return text
        return text[: budget - 1].rstrip() + "…"

    def _load_pixmap(self, path: str) -> QPixmap | None:
        if not path:
            return None
        cache_key = path
        if cache_key in self._pixmap_cache:
            cached = self._pixmap_cache[cache_key]
            return cached if not cached.isNull() else None
        if not Path(path).exists():
            self._pixmap_cache[cache_key] = QPixmap()
            return None
        pix = QPixmap(path)
        self._pixmap_cache[cache_key] = pix
        return pix if not pix.isNull() else None

    def clear_cache(self) -> None:
        self._pixmap_cache.clear()
