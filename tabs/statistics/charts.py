"""Widgets de gráficas Qt para el panel visual de estadísticas.

No requieren Matplotlib ni dependencias externas; se pintan con QPainter y pueden
exportarse directamente a PNG mediante QWidget.grab().
"""
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFontMetrics
from PyQt6.QtWidgets import QSizePolicy, QWidget


class BarChartWidget(QWidget):
    def __init__(self, title, *, horizontal=False, parent=None):
        super().__init__(parent)
        self.title = str(title)
        self.horizontal = bool(horizontal)
        self._items = []
        self.setMinimumHeight(240 if horizontal else 255)
        self.setMinimumWidth(420)
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
            self.setMinimumHeight(max(240, 58 + len(normalized) * 48))
            self.setMinimumWidth(420)
        else:
            # Conserva espacio legible para cada periodo; el contenedor puede
            # ofrecer desplazamiento horizontal cuando el rango sea extenso.
            self.setMinimumHeight(255)
            self.setMinimumWidth(max(420, 48 + len(normalized) * 58))
        self.updateGeometry()
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        surface = QColor("#ffffff")
        text = QColor("#20242b")
        muted = QColor("#d5dbe3")
        accent = QColor("#2563eb")
        border = QColor("#d7dde5")

        painter.fillRect(self.rect(), surface)
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
            painter.setPen(QColor("#687385"))
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
        # No se limita el número de instituciones ni facultades: el widget
        # crece verticalmente y su contenedor proporciona scroll.
        items = sorted(
            self._items,
            key=lambda item: (-item[1], item[0].casefold()),
        )
        maximum = max((value for _, value in items), default=1) or 1
        top = 44
        bottom = self.height() - 12
        row_height = max(48.0, (bottom - top) / max(1, len(items)))

        label_width = min(330, max(150, int(self.width() * 0.42)))
        bar_left = 14 + label_width
        value_area = 48
        bar_width = max(24, self.width() - bar_left - value_area - 18)
        label_font = painter.font()
        label_font.setBold(False)
        label_font.setPointSize(8)
        painter.setFont(label_font)
        metrics = QFontMetrics(label_font)

        for index, (label, value) in enumerate(items):
            y = top + index * row_height
            label_rect = QRectF(
                12,
                y + 1,
                max(80, label_width - 10),
                max(24, row_height - 2),
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
                max(7.0, row_height * 0.38),
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
        # Se muestran todos los periodos; el ancho mínimo permite desplazarse
        # horizontalmente en rangos largos en lugar de descartar fechas.
        items = self._items
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
                    label,
                    Qt.TextElideMode.ElideRight,
                    max(22, int(slot_width - 2)),
                ),
            )
