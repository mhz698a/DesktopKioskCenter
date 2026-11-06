"""Widgets de gráficas Qt para el panel visual de estadísticas.

No requieren Matplotlib ni dependencias externas; se pintan con QPainter y pueden
exportarse directamente a PNG mediante QWidget.grab().
"""
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFontMetrics
from PyQt6.QtWidgets import QSizePolicy, QWidget


THEMES = {
    "dark": {
        "background": "#202327",
        "surface": "#262b31",
        "text": "#e8edf2",
        "muted": "#414954",
        "accent": "#5b9bff",
        "border": "#414954",
        "secondary_text": "#aeb8c4",
    },
    "light": {
        "background": "#ffffff",
        "surface": "#ffffff",
        "text": "#20242b",
        "muted": "#d5dbe3",
        "accent": "#2563eb",
        "border": "#d7dde5",
        "secondary_text": "#687385",
    },
}


class BarChartWidget(QWidget):
    def __init__(
        self,
        title,
        *,
        horizontal=False,
        parent=None,
        theme="dark",
        compact=False,
        font_scale=1.0,
    ):
        super().__init__(parent)
        self.title = str(title)
        self.horizontal = bool(horizontal)
        self.theme = theme if theme in THEMES else "dark"
        self.compact = bool(compact)
        self.font_scale = float(font_scale)
        self._items = []
        self.setMinimumHeight(180 if compact else (240 if horizontal else 255))
        self.setMinimumWidth(1 if compact else 420)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

    def set_data(self, items):
        normalized = []
        for label, value in items:
            try:
                count = max(0, int(value))
            except (TypeError, ValueError):
                continue
            normalized.append((str(label), count))
        self._items = normalized

        if self.horizontal:
            row_height = 28 if self.compact else 48
            min_height = 58 + len(normalized) * row_height
            self.setMinimumHeight(max(180 if self.compact else 240, min_height))
            self.setMinimumWidth(1 if self.compact else 420)
        else:
            self.setMinimumHeight(210 if self.compact else 255)
            self.setMinimumWidth(
                1 if self.compact else max(420, 48 + len(normalized) * 58)
            )
        self.updateGeometry()
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        colors = THEMES[self.theme]
        surface = QColor(colors["surface"])
        text = QColor(colors["text"])
        muted = QColor(colors["muted"])
        accent = QColor(colors["accent"])
        border = QColor(colors["border"])

        painter.fillRect(self.rect(), QColor(colors["background"]))
        bounds = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        painter.setPen(QPen(border, 1))
        painter.setBrush(QBrush(surface))
        painter.drawRoundedRect(bounds, 8, 8)

        title_font = painter.font()
        title_font.setBold(True)
        base_title_size = max(9, title_font.pointSize())
        title_font.setPointSize(max(8, int(base_title_size * self.font_scale)))
        painter.setFont(title_font)
        painter.setPen(text)
        painter.drawText(
            QRectF(14, 10, max(0, self.width() - 28), 26),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.title,
        )

        if not self._items:
            painter.setPen(QColor(colors["secondary_text"]))
            painter.drawText(
                bounds.adjusted(12, 38, -12, -12),
                Qt.AlignmentFlag.AlignCenter,
                "No hay categorías con accesos en este periodo.",
            )
            return

        if self.horizontal:
            self._paint_horizontal(painter, text, muted, accent)
        else:
            self._paint_vertical(painter, text, muted, accent)

    def _paint_horizontal(self, painter, text, muted, accent):
        # No se limita el número de instituciones ni facultades.
        items = sorted(
            self._items,
            key=lambda item: (-item[1], item[0].casefold()),
        )
        maximum = max((value for _, value in items), default=1) or 1
        top = 44
        bottom = self.height() - 12
        min_row_height = 28 if self.compact else 48
        row_height = max(
            min_row_height,
            (bottom - top) / max(1, len(items)),
        )

        label_width = min(
            330 if not self.compact else 210,
            max(150, int(self.width() * 0.42)),
        )
        bar_left = 14 + label_width
        value_area = 42 if self.compact else 48
        bar_width = max(24, self.width() - bar_left - value_area - 18)

        label_font = painter.font()
        label_font.setBold(False)
        base_label_size = 7 if self.compact else 8
        label_font.setPointSize(max(6, int(base_label_size * self.font_scale)))
        painter.setFont(label_font)
        metrics = QFontMetrics(label_font)

        for index, (label, value) in enumerate(items):
            y = top + index * row_height
            label_rect = QRectF(
                12,
                y + 1,
                max(80, label_width - 10),
                max(22, row_height - 2),
            )
            painter.setPen(text)
            painter.drawText(
                label_rect,
                int(Qt.AlignmentFlag.AlignLeft)
                | int(Qt.AlignmentFlag.AlignVCenter)
                | int(Qt.TextFlag.TextWordWrap),
                label,
            )

            bar_rect = QRectF(
                bar_left,
                y + row_height * 0.31,
                bar_width,
                max(6.0, row_height * 0.38),
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(muted))
            painter.drawRoundedRect(bar_rect, 4, 4)

            value_width = bar_width * (value / maximum)
            if value_width > 0:
                painter.setBrush(QBrush(accent))
                painter.drawRoundedRect(
                    QRectF(
                        bar_left,
                        bar_rect.y(),
                        value_width,
                        bar_rect.height(),
                    ),
                    4,
                    4,
                )

            painter.setPen(text)
            painter.drawText(
                QRectF(
                    bar_left + bar_width + 5,
                    y,
                    value_area,
                    row_height,
                ),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                metrics.elidedText(
                    str(value),
                    Qt.TextElideMode.ElideRight,
                    value_area,
                ),
            )

    def _paint_vertical(self, painter, text, muted, accent):
        # Se muestran todos los periodos, también en las imágenes de PDF.
        items = self._items
        maximum = max((value for _, value in items), default=1) or 1
        left, right = 28, self.width() - 14
        top, bottom = 48, self.height() - 38
        chart_width = max(1, right - left)
        chart_height = max(1, bottom - top)

        label_font = painter.font()
        base_vert_size = 7 if self.compact else label_font.pointSize()
        label_font.setPointSize(max(6, int(base_vert_size * self.font_scale)))
        painter.setFont(label_font)
        metrics = QFontMetrics(label_font)

        count = len(items)
        slot_width = chart_width / max(1, count)
        bar_width = max(3.0, min(28.0, slot_width * 0.62))
        metrics = QFontMetrics(label_font)

        for index, (label, value) in enumerate(items):
            center_x = left + slot_width * (index + 0.5)
            bar_height = chart_height * (value / maximum)
            bar_rect = QRectF(
                center_x - bar_width / 2,
                bottom - bar_height,
                bar_width,
                max(1.0, bar_height),
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(accent))
            painter.drawRoundedRect(bar_rect, 3, 3)

            painter.setPen(text)
            painter.drawText(
                QRectF(center_x - slot_width / 2, bottom + 5, slot_width, 25),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                metrics.elidedText(
                    label,
                    Qt.TextElideMode.ElideRight,
                    max(10, int(slot_width - 2)),
                ),
            )
