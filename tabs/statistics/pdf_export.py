"""Exportación de reportes de estadísticas a PDF con páginas compuestas."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path

from PyQt6.QtCore import QRectF, QSize, Qt, QMarginsF
from PyQt6.QtGui import (
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
    build_chart_data,
    build_zero_access_data,
    university_group_label,
)


GROUPING_TITLES = {
    "day": "Accesos por día",
    "week": "Accesos por semana",
    "month": "Accesos por mes",
}
CHART_CHUNK_SIZE = 12
ZERO_LIST_CHUNK_SIZE = 12
TABLE_HEADERS = ("Periodo", "Universidad", "Detalle / facultad", "Accesos")


def _chunks(items, chunk_size):
    items = list(items)
    return [
        items[start:start + chunk_size]
        for start in range(0, len(items), chunk_size)
    ]


def _chart_image(title, values, *, width, height, horizontal=True):
    """Renderiza una gráfica clara ajustada exactamente al espacio disponible."""
    chart = BarChartWidget(
        title,
        horizontal=horizontal,
        theme="light",
        compact=True,
    )
    chart.set_data(values)
    # La exportación define el tamaño del recuadro. Se evita que los mínimos
    # pensados para el scroll de la interfaz fuercen un widget mayor que la hoja.
    chart.setMinimumWidth(1)
    chart.setMinimumHeight(1)
    chart.resize(max(1, int(width)), max(1, int(height)))
    chart.ensurePolished()

    image = QImage(
        QSize(max(1, int(width)), max(1, int(height))),
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
        source = str(row.get("source") or "Sin especificar")
        university = university_group_label(row)
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


def _draw_cell(painter, rect, text, *, font, background=None, align=None):
    flags = (
        int(Qt.AlignmentFlag.AlignLeft)
        | int(Qt.AlignmentFlag.AlignVCenter)
        | int(Qt.TextFlag.TextWordWrap)
    )
    if align is not None:
        flags = int(align) | int(Qt.TextFlag.TextWordWrap)
    painter.setFont(font)
    painter.setPen(QPen(QColor("#cbd2da"), 1))
    if background is not None:
        painter.fillRect(rect, background)
    painter.drawRect(rect)
    painter.setPen(QColor("#20242b"))
    painter.drawText(rect.adjusted(6, 3, -6, -3), flags, str(text))


def export_statistics_pdf(
    filename,
    *,
    start_date,
    end_date,
    reports,
    catalog=None,
):
    """Genera un PDF A4 horizontal, con tres gráficas por hoja y tablas completas.

    Las cuatro áreas de cada página de gráficas son: periodo, procedencia general,
    facultades y catálogo de entidades sin accesos. Los datos se dividen en bloques
    para que ninguna categoría desaparezca cuando hay muchas instituciones.
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
            QPageLayout.Orientation.Landscape,
            QMarginsF(16, 16, 16, 16),
            QPageLayout.Unit.Millimeter,
        )
    )

    dpi = writer.resolution()
    page_rect = QRectF(writer.pageLayout().paintRectPixels(dpi))
    left = page_rect.left()
    top = page_rect.top()
    width = page_rect.width()
    right = page_rect.right()
    bottom = page_rect.bottom()

    title_font = QFont("Arial", 13, QFont.Weight.Bold)
    subtitle_font = QFont("Arial", 8)
    section_font = QFont("Arial", 9, QFont.Weight.Bold)
    body_font = QFont("Arial", 8)
    small_font = QFont("Arial", 7)

    painter = QPainter()
    if not painter.begin(writer):
        raise OSError("Qt no pudo iniciar el dispositivo de escritura PDF.")
    painter.setClipRect(page_rect)

    page_count = 0

    def begin_page(title, subtitle=""):
        nonlocal page_count
        if page_count:
            if not writer.newPage():
                raise OSError("Qt no pudo crear una nueva página del PDF.")
        page_count += 1
        painter.save()
        painter.setClipRect(page_rect)
        painter.fillRect(page_rect, QColor("#ffffff"))
        painter.setPen(QColor("#20242b"))
        painter.setFont(title_font)
        painter.drawText(
            QRectF(left, top, width, 27),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            title,
        )
        y = top + 30
        if subtitle:
            painter.setFont(subtitle_font)
            painter.setPen(QColor("#596575"))
            painter.drawText(
                QRectF(left, y, width, 18),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                subtitle,
            )
            y += 21
        painter.setPen(QColor("#20242b"))
        painter.restore()
        return y

    def draw_chart_slot(rect, title, values, *, placeholder):
        rect = rect.intersected(page_rect)
        if rect.width() <= 2 or rect.height() <= 2:
            return
        if values:
            image = _chart_image(
                title,
                values,
                width=int(rect.width()),
                height=int(rect.height()),
                horizontal=True,
            )
            painter.drawImage(rect.topLeft(), image)
            return
        painter.save()
        painter.setClipRect(rect)
        painter.fillRect(rect, QColor("#ffffff"))
        painter.setPen(QPen(QColor("#d7dde5"), 1))
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 7, 7)
        painter.setFont(section_font)
        painter.setPen(QColor("#20242b"))
        painter.drawText(
            rect.adjusted(12, 10, -12, -10),
            int(Qt.AlignmentFlag.AlignHCenter)
            | int(Qt.AlignmentFlag.AlignVCenter)
            | int(Qt.TextFlag.TextWordWrap),
            placeholder,
        )
        painter.restore()

    def draw_zero_slot(rect, items):
        rect = rect.intersected(page_rect)
        painter.save()
        painter.setClipRect(rect)
        painter.fillRect(rect, QColor("#ffffff"))
        painter.setPen(QPen(QColor("#d7dde5"), 1))
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 7, 7)
        painter.setFont(section_font)
        painter.setPen(QColor("#20242b"))
        painter.drawText(
            QRectF(rect.left() + 12, rect.top() + 8, rect.width() - 24, 22),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "Entidades registradas sin accesos",
        )

        if not items:
            painter.setFont(body_font)
            painter.setPen(QColor("#687385"))
            painter.drawText(
                rect.adjusted(12, 36, -12, -8),
                int(Qt.AlignmentFlag.AlignHCenter)
                | int(Qt.AlignmentFlag.AlignVCenter),
                "No hay universidades ni facultades con cero accesos.",
            )
            painter.restore()
            return

        y = rect.top() + 35
        available_height = max(1, rect.bottom() - y - 6)
        row_height = available_height / max(1, len(items))
        for index, (kind, name) in enumerate(items):
            row_rect = QRectF(
                rect.left() + 12,
                y + index * row_height,
                rect.width() - 24,
                row_height,
            )
            painter.setFont(small_font)
            painter.setPen(QColor("#20242b"))
            painter.drawText(
                row_rect,
                int(Qt.AlignmentFlag.AlignLeft)
                | int(Qt.AlignmentFlag.AlignVCenter)
                | int(Qt.TextFlag.TextWordWrap),
                f"{kind}: {name}",
            )
        painter.restore()

    def draw_dashboard(grouping, rows, catalog, *, include_zero):
        period_data, general_data, faculty_data = build_chart_data(
            rows,
            grouping,
        )
        period_chunks = _chunks(period_data, CHART_CHUNK_SIZE)
        general_chunks = _chunks(general_data, CHART_CHUNK_SIZE)
        faculty_chunks = _chunks(faculty_data, CHART_CHUNK_SIZE)

        zero_access = (
            build_zero_access_data(rows, catalog)
            if include_zero else {"universities": [], "faculties": []}
        )
        zero_items = [
            ("Universidad", name)
            for name in zero_access.get("universities", [])
        ] + [
            ("Facultad UAQ", name)
            for name in zero_access.get("faculties", [])
        ]
        zero_chunks = _chunks(zero_items, ZERO_LIST_CHUNK_SIZE)

        page_total = max(
            1,
            len(period_chunks),
            len(general_chunks),
            len(faculty_chunks),
            len(zero_chunks),
        )
        for page_index in range(page_total):
            page_subtitle = (
                f"{start_date} a {end_date} · hoja de gráficas "
                f"{page_index + 1} de {page_total}"
            )
            grid_top = begin_page(
                f"Estadísticas · {GROUPING_TITLES[grouping]}",
                page_subtitle,
            ) + 4
            gap = 12
            slot_width = (width - gap) / 2
            slot_height = (bottom - grid_top - gap) / 2

            slots = (
                QRectF(left, grid_top, slot_width, slot_height),
                QRectF(left + slot_width + gap, grid_top, slot_width, slot_height),
                QRectF(left, grid_top + slot_height + gap, slot_width, slot_height),
                QRectF(
                    left + slot_width + gap,
                    grid_top + slot_height + gap,
                    slot_width,
                    slot_height,
                ),
            )

            period_values = (
                period_chunks[page_index]
                if page_index < len(period_chunks) else []
            )
            general_values = (
                general_chunks[page_index]
                if page_index < len(general_chunks) else []
            )
            faculty_values = (
                faculty_chunks[page_index]
                if page_index < len(faculty_chunks) else []
            )
            zero_values = (
                zero_chunks[page_index]
                if page_index < len(zero_chunks) else []
            )

            draw_chart_slot(
                slots[0],
                f"Accesos por periodo · bloque {page_index + 1}",
                period_values,
                placeholder="No hay periodos con accesos.",
            )
            draw_chart_slot(
                slots[1],
                f"Procedencia general · bloque {page_index + 1}",
                general_values,
                placeholder="No hay universidades con accesos positivos.",
            )
            draw_chart_slot(
                slots[2],
                f"Procedencia por facultad · bloque {page_index + 1}",
                faculty_values,
                placeholder="No hay facultades con accesos positivos.",
            )
            draw_zero_slot(slots[3], zero_values)

    def draw_detail_tables(rows, grouping):
        groups = _group_detail_rows(rows)
        if not groups:
            return

        y = begin_page(
            "Detalle de accesos",
            f"{GROUPING_TITLES[grouping]} · agrupado por universidad · "
            f"fechas ascendentes · {start_date} a {end_date}",
        )
        col_width = width / 4
        header_height = 26
        group_height = 27
        header_background = QColor("#e9edf2")
        group_background = QColor("#e2eaf5")

        def draw_group_title(name, continuation=False):
            nonlocal y
            label = f"Universidad: {name}"
            if continuation:
                label += " (continuación)"
            rect = QRectF(left, y, width, group_height)
            painter.save()
            painter.setClipRect(page_rect)
            painter.fillRect(rect, group_background)
            painter.setPen(QPen(QColor("#cbd2da"), 1))
            painter.drawRect(rect)
            painter.setFont(section_font)
            painter.setPen(QColor("#25364a"))
            painter.drawText(
                rect.adjusted(7, 2, -7, -2),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                label,
            )
            painter.restore()
            y += group_height

        def draw_header_row():
            nonlocal y
            for column, header in enumerate(TABLE_HEADERS):
                rect = QRectF(
                    left + column * col_width,
                    y,
                    col_width,
                    header_height,
                )
                _draw_cell(
                    painter,
                    rect,
                    header,
                    font=QFont("Arial", 8, QFont.Weight.Bold),
                    background=header_background,
                )
            y += header_height

        for university, group_rows in groups:
            if y + group_height + header_height + 35 > bottom:
                y = begin_page(
                    "Detalle de accesos · continuación",
                    f"{GROUPING_TITLES[grouping]} · fechas ascendentes",
                )
            draw_group_title(university)
            draw_header_row()

            for record in group_rows:
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
                        max(1, int(col_width - 14)),
                        4000,
                        int(Qt.AlignmentFlag.AlignLeft)
                        | int(Qt.TextFlag.TextWordWrap),
                        str(value),
                    )
                    heights.append(bounds.height())
                row_height = max(25, max(heights, default=0) + 8)

                if y + row_height > bottom:
                    y = begin_page(
                        "Detalle de accesos · continuación",
                        f"Universidad: {university} · fechas ascendentes",
                    )
                    draw_group_title(university, continuation=True)
                    draw_header_row()

                painter.save()
                painter.setClipRect(page_rect)
                for column, value in enumerate(values):
                    rect = QRectF(
                        left + column * col_width,
                        y,
                        col_width,
                        row_height,
                    )
                    _draw_cell(
                        painter,
                        rect,
                        value,
                        font=small_font if column < 3 else body_font,
                        background=QColor("#ffffff"),
                        align=(
                            Qt.AlignmentFlag.AlignRight
                            if column == 3
                            else Qt.AlignmentFlag.AlignLeft
                        ),
                    )
                painter.restore()
                y += row_height
            y += 10

    try:
        for report_index, (grouping, rows) in enumerate(selected_reports):
            draw_dashboard(
                grouping,
                rows,
                catalog,
                include_zero=(report_index == 0),
            )
            if rows:
                draw_detail_tables(rows, grouping)
    finally:
        painter.end()

    if not output_path.is_file() or output_path.stat().st_size < 5:
        raise OSError("Qt no pudo generar el archivo PDF solicitado.")

    with output_path.open("rb") as pdf_file:
        if pdf_file.read(5) != b"%PDF-":
            raise OSError("Qt generó un archivo, pero no tiene una cabecera PDF válida.")

    return output_path
