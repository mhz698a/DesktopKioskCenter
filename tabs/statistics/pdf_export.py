"""Exportación paginada de reportes de estadísticas a PDF."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QImage,
    QPainter,
    QPen,
    QPageLayout,
    QPageSize,
    QPdfWriter,
)

from tabs.statistics.charts import BarChartWidget
from tabs.statistics.report_data import (
    UAQ_FULL_NAME,
    build_chart_data,
    build_zero_access_data,
)


GROUPING_TITLES = {
    "day": "Accesos por día",
    "week": "Accesos por semana",
    "month": "Accesos por mes",
}
CHART_CHUNK_SIZE = 12
TABLE_HEADERS = ("Periodo", "Universidad", "Detalle / facultad", "Accesos")


def _chart_image(title, values, *, horizontal=False):
    """Renderiza una gráfica completa con fondo blanco."""
    chart = BarChartWidget(title, horizontal=horizontal)
    chart.set_data(values)
    width = 1400
    height = (
        max(250, 58 + len(values) * 36)
        if horizontal
        else 390
    )
    chart.resize(width, height)
    chart.ensurePolished()

    image = QImage(
        QSize(width, height),
        QImage.Format.Format_ARGB32_Premultiplied,
    )
    image.fill(QColor("#ffffff"))

    painter = QPainter(image)
    try:
        chart.render(painter)
    finally:
        painter.end()
        chart.close()
        chart.deleteLater()
    return image


def _chunks(items, chunk_size=CHART_CHUNK_SIZE):
    items = list(items)
    for start in range(0, len(items), chunk_size):
        yield start, items[start:start + chunk_size]


def _display_period(value, grouping):
    raw = str(value or "")
    try:
        if grouping in ("day", "week"):
            parsed = date.fromisoformat(raw[:10])
            formatted = parsed.strftime("%d/%m/%Y")
            return f"Semana del {formatted}" if grouping == "week" else formatted
        if grouping == "month" and len(raw) >= 7:
            return f"{raw[5:7]}/{raw[:4]}"
    except ValueError:
        pass
    return raw


def _group_detail_rows(rows):
    """Agrupa por institución y conserva las fechas en orden ascendente."""
    groups = defaultdict(list)
    for row in rows:
        origin = str(row.get("origin") or "Sin clasificar")
        source = str(row.get("source") or "Sin especificar")
        if origin == "UAQ":
            university = UAQ_FULL_NAME
        elif origin == "Universidad":
            university = source or "Universidad no especificada"
        elif origin == "Público en general":
            university = "Público en general"
        else:
            university = origin

        groups[university].append({
            "period": str(row.get("period") or ""),
            "university": university,
            "detail": source,
            "total": int(row.get("total") or 0),
        })

    return [
        (university, sorted(group_rows, key=lambda item: item["period"]))
        for university, group_rows in sorted(
            groups.items(),
            key=lambda item: item[0].casefold(),
        )
    ]


def _draw_wrapped_cell(painter, rect, text, *, font, background=None):
    flags = (
        Qt.AlignmentFlag.AlignLeft
        | Qt.AlignmentFlag.AlignVCenter
        | Qt.TextFlag.TextWordWrap
    )
    painter.setFont(font)
    painter.setPen(QPen(QColor("#cbd2da"), 1))
    if background is not None:
        painter.fillRect(rect, background)
    painter.drawRect(rect)
    painter.setPen(QColor("#20242b"))
    painter.drawText(rect.adjusted(7, 3, -7, -3), flags, str(text))


def export_statistics_pdf(
    filename,
    *,
    start_date,
    end_date,
    reports,
    catalog=None,
):
    """Crea un PDF paginado con gráficas completas, catálogos y tablas agrupadas.

    reports tiene la forma:
        {"day": [filas SQL], "week": [filas SQL], "month": [filas SQL]}
    """
    output_path = Path(filename).expanduser()
    if output_path.suffix.lower() != ".pdf":
        output_path = output_path.with_suffix(".pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    selected_reports = [
        (grouping, list(rows))
        for grouping, rows in reports.items()
        if grouping in GROUPING_TITLES
    ]
    if not selected_reports:
        raise ValueError("No hay periodos seleccionados para exportar.")

    catalog = catalog or {}
    if output_path.exists():
        output_path.unlink()

    writer = QPdfWriter(str(output_path))
    writer.setTitle("Reporte de accesos - DesktopKioskCenter")
    writer.setCreator("DesktopKioskCenter")
    writer.setResolution(144)
    writer.setPageLayout(
        QPageLayout(
            QPageSize(QPageSize.PageSizeId.A4),
            QPageLayout.Orientation.Portrait,
            QMarginsF(14, 14, 14, 14),
        )
    )

    dpi = writer.resolution()
    page_rect = QRectF(writer.pageLayout().paintRectPixels(dpi))
    content = page_rect.adjusted(0, 0, 0, 0)
    left = content.left()
    top = content.top()
    width = content.width()
    bottom = content.bottom()
    title_font = QFont("Arial", 16, QFont.Weight.Bold)
    subtitle_font = QFont("Arial", 9)
    section_font = QFont("Arial", 11, QFont.Weight.Bold)
    body_font = QFont("Arial", 9)
    small_font = QFont("Arial", 8)

    painter = QPainter()
    if not painter.begin(writer):
        raise OSError("Qt no pudo iniciar el dispositivo de escritura PDF.")

    page_count = 0

    def begin_page(title, subtitle=""):
        nonlocal page_count
        if page_count:
            if not writer.newPage():
                raise OSError("Qt no pudo crear una nueva página del PDF.")
        page_count += 1
        painter.fillRect(page_rect, QColor("#ffffff"))
        painter.setPen(QColor("#20242b"))
        painter.setFont(title_font)
        painter.drawText(
            QRectF(left, top, width, 38),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            title,
        )
        y = top + 43
        if subtitle:
            painter.setFont(subtitle_font)
            painter.setPen(QColor("#596575"))
            painter.drawText(
                QRectF(left, y, width, 25),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                subtitle,
            )
            y += 29
        painter.setPen(QColor("#20242b"))
        return y

    def draw_chart_page(group_title, chart_title, values, *, horizontal, offset, total):
        end = offset + len(values)
        suffix = (
            f" · categorías {offset + 1}–{end} de {total}"
            if total > len(values)
            else ""
        )
        y = begin_page(
            group_title,
            f"{chart_title}{suffix} | {start_date} a {end_date}",
        )
        image = _chart_image(chart_title, values, horizontal=horizontal)
        target = QRectF(
            left + 2,
            y + 5,
            max(1, width - 4),
            max(1, bottom - y - 8),
        )
        scaled = image.scaled(
            QSize(max(1, int(target.width())), max(1, int(target.height()))),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = target.left() + (target.width() - scaled.width()) / 2
        y_image = target.top() + (target.height() - scaled.height()) / 2
        painter.drawImage(QPointF(x, y_image), scaled)

    def draw_zero_access_pages(zero_access, grouping):
        university_names = list(zero_access.get("universities", []))
        faculty_names = list(zero_access.get("faculties", []))
        sections = []
        if university_names:
            sections.append(("Universidades sin accesos", university_names))
        if faculty_names:
            sections.append(("Facultades UAQ sin accesos", faculty_names))
        if not sections:
            return

        y = begin_page(
            f"Entidades sin accesos · {GROUPING_TITLES[grouping]}",
            f"Catálogo registrado sin actividad entre {start_date} y {end_date}",
        )
        line_height = 28
        label_width = width - 20

        for section_title, names in sections:
            if y + 42 > bottom:
                y = begin_page(
                    f"Entidades sin accesos · {GROUPING_TITLES[grouping]} · continuación"
                )
            painter.setFont(section_font)
            painter.setPen(QColor("#25364a"))
            painter.drawText(
                QRectF(left + 4, y, label_width, 30),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"{section_title} ({len(names)})",
            )
            y += 32

            for name in names:
                label = f"• {name}"
                metrics = QFontMetrics(body_font)
                bounds = metrics.boundingRect(
                    0,
                    0,
                    int(label_width - 16),
                    4000,
                    int(
                        Qt.AlignmentFlag.AlignLeft
                        | Qt.TextFlag.TextWordWrap
                    ),
                    label,
                )
                row_height = max(line_height, bounds.height() + 10)
                if y + row_height > bottom:
                    y = begin_page(
                        f"Entidades sin accesos · {GROUPING_TITLES[grouping]} · continuación",
                        section_title,
                    )
                    painter.setFont(section_font)
                    painter.setPen(QColor("#25364a"))
                    painter.drawText(
                        QRectF(left + 4, y, label_width, 30),
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        f"{section_title} (continuación)",
                    )
                    y += 32

                painter.setFont(body_font)
                painter.setPen(QColor("#20242b"))
                painter.drawText(
                    QRectF(left + 12, y, label_width - 12, row_height),
                    Qt.AlignmentFlag.AlignLeft
                    | Qt.AlignmentFlag.AlignVCenter
                    | Qt.TextFlag.TextWordWrap,
                    label,
                )
                y += row_height

    def draw_detail_tables(rows, grouping):
        groups = _group_detail_rows(rows)
        if not groups:
            return

        y = begin_page(
            "Detalle de accesos",
            f"{GROUPING_TITLES[grouping]} · agrupado por universidad · "
            f"{start_date} a {end_date}",
        )
        col_width = width / 4
        headers = TABLE_HEADERS
        row_background = QColor("#ffffff")
        header_background = QColor("#e9edf2")
        group_background = QColor("#e2eaf5")

        def draw_group_title(name, continuation=False):
            nonlocal y
            title = f"Universidad: {name}"
            if continuation:
                title += " (continuación)"
            rect = QRectF(left, y, width, 32)
            painter.fillRect(rect, group_background)
            painter.setPen(QPen(QColor("#cbd2da"), 1))
            painter.drawRect(rect)
            painter.setFont(section_font)
            painter.setPen(QColor("#25364a"))
            painter.drawText(
                rect.adjusted(8, 2, -8, -2),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                title,
            )
            y += 32

        def draw_header_row():
            nonlocal y
            for column, header in enumerate(headers):
                rect = QRectF(
                    left + column * col_width,
                    y,
                    col_width,
                    30,
                )
                _draw_wrapped_cell(
                    painter,
                    rect,
                    header,
                    font=QFont("Arial", 8, QFont.Weight.Bold),
                    background=header_background,
                )
            y += 30

        for university, group_rows in groups:
            # Mantiene juntas la etiqueta y la cabecera de cada grupo.
            if y + 70 > bottom:
                y = begin_page(
                    "Detalle de accesos · continuación",
                    f"{GROUPING_TITLES[grouping]} · fechas ascendentes",
                )
            draw_group_title(university)
            draw_header_row()

            for row_index, record in enumerate(group_rows):
                values = (
                    _display_period(record["period"], grouping),
                    university,
                    record["detail"],
                    f'{record["total"]:,}',
                )
                metrics = QFontMetrics(body_font)
                heights = []
                for value in values:
                    bounds = metrics.boundingRect(
                        0,
                        0,
                        int(col_width - 14),
                        4000,
                        int(
                            Qt.AlignmentFlag.AlignLeft
                            | Qt.TextFlag.TextWordWrap
                        ),
                        str(value),
                    )
                    heights.append(bounds.height())
                row_height = max(32, max(heights, default=0) + 10)

                if y + row_height > bottom:
                    y = begin_page(
                        "Detalle de accesos · continuación",
                        f"Universidad: {university} · fechas ascendentes",
                    )
                    draw_group_title(university, continuation=True)
                    draw_header_row()

                for column, value in enumerate(values):
                    rect = QRectF(
                        left + column * col_width,
                        y,
                        col_width,
                        row_height,
                    )
                    _draw_wrapped_cell(
                        painter,
                        rect,
                        value,
                        font=small_font if column < 3 else body_font,
                        background=row_background,
                    )
                y += row_height

            y += 14

    try:
        for grouping, rows in selected_reports:
            period_data, general_data, faculty_data = build_chart_data(
                rows,
                grouping,
            )
            total_categories = (
                ("Accesos por periodo", period_data, False),
                ("Procedencia general", general_data, True),
                ("Procedencia por facultad", faculty_data, True),
            )

            for chart_title, values, horizontal in total_categories:
                for offset, chunk in _chunks(values):
                    draw_chart_page(
                        GROUPING_TITLES[grouping],
                        chart_title,
                        chunk,
                        horizontal=horizontal,
                        offset=offset,
                        total=len(values),
                    )

            zero_access = build_zero_access_data(rows, catalog)
            draw_zero_access_pages(zero_access, grouping)
            draw_detail_tables(rows, grouping)
    finally:
        painter.end()

    if not output_path.is_file() or output_path.stat().st_size < 5:
        raise OSError("Qt no pudo generar el archivo PDF solicitado.")

    with output_path.open("rb") as pdf_file:
        if pdf_file.read(5) != b"%PDF-":
            raise OSError("Qt generó un archivo, pero no tiene una cabecera PDF válida.")

    return output_path
