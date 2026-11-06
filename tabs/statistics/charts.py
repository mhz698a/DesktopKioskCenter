"""Widgets de gráficas Qt para el panel visual de estadísticas.

No requieren Matplotlib ni dependencias externas; se pintan con QPainter y pueden
exportarse directamente a PNG mediante QWidget.grab().
"""
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QPen, QBrush, QFontMetrics, QPalette
from PyQt6.QtWidgets import QSizePolicy, QWidget


class BarChartWidget(QWidget):
    def __init__(self, title, *, horizontal=False, parent=None):
        super().__init__(parent)
        self.title = str(title)
        self.horizontal = bool(horizontal)
        self._items = []
        self.setMinimumHeight(220 if horizontal else 235)
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
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        palette = self.palette()
        surface = palette.color(QPalette.ColorRole.Base)
        text = palette.color(QPalette.ColorRole.Text)
        muted = palette.color(QPalette.ColorRole.Mid)
        accent = palette.color(QPalette.ColorRole.Highlight)
        border = palette.color(QPalette.ColorRole.Mid)

        bounds = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        painter.setPen(QPen(border, 1))
        painter.setBrush(QBrush(surface))
        painter.drawRoundedRect(bounds, 8, 8)

        title_font = painter.font()
        title_font.setBold(True)
        title_font.setPointSize(max(9, title_font.pointSize()))
        painter.setFont(title_font)
        painter.setPen(text)
        painter.drawText(
            QRectF(14, 10, max(0, self.width() - 28), 26),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.title,
        )

        if not self._items:
            painter.setPen(muted)
            painter.drawText(
                bounds.adjusted(12, 38, -12, -12),
                Qt.AlignmentFlag.AlignCenter,
                "Genera un reporte para visualizar los datos.",
            )
            return

        if self.horizontal:
            self._paint_horizontal(painter, text, muted, accent, surface)
        else:
            self._paint_vertical(painter, text, muted, accent)

    def _paint_horizontal(self, painter, text, muted, accent, surface):
        items = sorted(self._items, key=lambda item: item[1], reverse=True)[:8]
        maximum = max((value for _, value in items), default=1) or 1
        top = 44
        bottom = self.height() - 14
        row_height = max(18, (bottom - top) / max(1, len(items)))
        label_width = min(130, max(84, int(self.width() * 0.40)))
        bar_left = 14 + label_width
        bar_width = max(28, self.width() - bar_left - 43)
        metrics = QFontMetrics(painter.font())
        label_color = text
        max_label = max(28, label_width - 8)

        for index, (label, value) in enumerate(items):
            y = top + index * row_height
            label_rect = QRectF(12, y, label_width, row_height)
            painter.setPen(label_color)
            painter.drawText(
                label_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                metrics.elidedText(
                    label, Qt.TextElideMode.ElideRight, max_label
                ),
            )

            bar_rect = QRectF(bar_left, y + row_height * 0.23, bar_width, row_height * 0.54)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(muted))
            painter.drawRoundedRect(bar_rect, 4, 4)

            value_width = bar_width * (value / maximum)
            if value_width > 0:
                painter.setBrush(QBrush(accent))
                painter.drawRoundedRect(
                    QRectF(bar_left, bar_rect.y(), value_width, bar_rect.height()),
                    4, 4,
                )

            painter.setPen(text)
            painter.drawText(
                QRectF(bar_left + bar_width + 5, y, 32, row_height),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                str(value),
            )

    def _paint_vertical(self, painter, text, muted, accent):
        items = self._items[-14:]
        maximum = max((value for _, value in items), default=1) or 1
        left, right = 28, self.width() - 14
        top, bottom = 48, self.height() - 38
        chart_width = max(1, right - left)
        chart_height = max(1, bottom - top)

        painter.setFont(self.font())
        painter.setPen(QPen(muted, 1, Qt.PenStyle.DotLine))
        for tick in range(1, 5):
            y = bottom - chart_height * tick / 4
            painter.drawLine(int(left), int(y), int(right), int(y))

        count = len(items)
        slot_width = chart_width / max(1, count)
        bar_width = max(5.0, min(28.0, slot_width * 0.62))
        metrics = QFontMetrics(painter.font())

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
                    label, Qt.TextElideMode.ElideRight,
                    max(22, int(slot_width - 2)),
                ),
            )
