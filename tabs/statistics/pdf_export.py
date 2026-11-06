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
CHART_CHUNK_SIZE = 10
ZERO_LIST_CHUNK_SIZE = 10
TABLE_HEADERS = ("Periodo", "Detalle / facultad", "Accesos")
COLUMN_RATIOS = (0.25, 0.63, 0.12)


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
        font_scale=1.85,
    )
    chart.set_data(values)
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
    painter.drawText(rect.adjusted(4, 2, -4, -2), flags, str(text))


def export_statistics_pdf(
    filename,
    *,
    start_date,
    end_date,
    reports,
    catalog=None,
    paper_size="letter"
):
    """Genera un PDF vertical en tamaño Carta, con diseño ajustado a los márgenes."""
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
    normalized_paper_size = str(paper_size or "letter").strip().lower()
    paper_sizes = {
        "letter": (QPageSize.PageSizeId.Letter, "Carta"),
        "carta": (QPageSize.PageSizeId.Letter, "Carta"),
        "a4": (QPageSize.PageSizeId.A4, "A4"),
    }
    if normalized_paper_size not in paper_sizes:
        normalized_paper_size = "letter"
    page_size_id, page_size_label = paper_sizes[normalized_paper_size]

    if output_path.exists():
        output_path.unlink()

    writer = QPdfWriter(str(output_path))
    writer.setTitle(
        f"Reporte de accesos - DesktopKioskCenter ({page_size_label})"
    )
    writer.setCreator("DesktopKioskCenter")
    writer.setResolution(144)
    writer.setPageLayout(
        QPageLayout(
            QPageSize(page_size_id),
            QPageLayout.Orientation.Portrait,
            QMarginsF(5, 5, 5, 5),
            QPageLayout.Unit.Millimeter,
        )
    )

    dpi = writer.resolution()
    page_rect = QRectF(writer.pageLayout().paintRectPixels(dpi))
    left = page_rect.left()
    top = page_rect.top()
    width = page_rect.width() - (page_rect.width() * 0.05)
    bottom = page_rect.bottom() - (page_rect.bottom() * 0.05)

    title_font = QFont("Arial", 16, QFont.Weight.Bold)
    subtitle_font = QFont("Arial", 12)
    section_font = QFont("Arial", 11, QFont.Weight.Bold)
    body_font = QFont("Arial", 10) # cells

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
            QRectF(left, top, width, 36),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            title,
        )
        y = top + 40
        if subtitle:
            painter.setFont(subtitle_font)
            painter.setPen(QColor("#596575"))
            painter.drawText(
                QRectF(left, y, width, 26),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                subtitle,
            )
            y += 30
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
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 6, 6)
        painter.setFont(section_font)
        painter.setPen(QColor("#20242b"))
        painter.drawText(
            rect.adjusted(8, 6, -8, -6),
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
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 6, 6)
        painter.setFont(section_font)
        painter.setPen(QColor("#20242b"))
        painter.drawText(
            QRectF(rect.left() + 8, rect.top() + 6, rect.width() - 16, 20),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "Entidades sin accesos",
        )

        if not items:
            painter.setFont(body_font)
            painter.setPen(QColor("#687385"))
            painter.drawText(
                rect.adjusted(8, 28, -8, -4),
                int(Qt.AlignmentFlag.AlignHCenter)
                | int(Qt.AlignmentFlag.AlignVCenter),
                "No hay registros con cero accesos.",
            )
            painter.restore()
            return

        y_pos = rect.top() + 28
        available_height = max(1, rect.bottom() - y_pos - 4)
        row_height = available_height / max(1, len(items))
        for index, (kind, name) in enumerate(items):
            row_rect = QRectF(
                rect.left() + 8,
                y_pos + index * row_height,
                rect.width() - 16,
                row_height,
            )
            painter.setFont(body_font)
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
        chart_groups = (
            (
                "Accesos por periodo",
                _chunks(period_data, CHART_CHUNK_SIZE),
            ),
            (
                "Procedencia general",
                _chunks(general_data, CHART_CHUNK_SIZE),
            ),
            (
                "Facultades",
                _chunks(faculty_data, CHART_CHUNK_SIZE),
            ),
        )
        chart_items = []
        max_chunks = max((len(chunks) for _title, chunks in chart_groups), default=0)
        for chunk_index in range(max_chunks):
            for title, chunks in chart_groups:
                if chunk_index < len(chunks):
                    chart_items.append((
                        f"{title} · bloque {chunk_index + 1}",
                        chunks[chunk_index],
                    ))

        zero_access = (
            build_zero_access_data(rows, catalog)
            if include_zero else {"universities": [], "faculties": []}
        )
        zero_items = [
            ("Universidad", name)
            for name in zero_access.get("universities", [])
        ] + [
            ("Facultad", name)
            for name in zero_access.get("faculties", [])
        ]
        zero_chunks = _chunks(zero_items, ZERO_LIST_CHUNK_SIZE)

        chart_page_count = max(1, (len(chart_items) + 2) // 3)
        page_total = max(chart_page_count, len(zero_chunks))
        for page_index in range(page_total):
            page_subtitle = (
                f"{start_date} a {end_date} · pág. {page_index + 1} de {page_total}"
            )
            grid_top = begin_page(
                f"Estadísticas · {GROUPING_TITLES[grouping]}",
                page_subtitle,
            ) + 2
            gap = 8
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

            zero_values = (
                zero_chunks[page_index]
                if page_index < len(zero_chunks) else []
            )

            for slot_index in range(3):
                item_index = page_index * 3 + slot_index
                if item_index < len(chart_items):
                    chart_title, chart_values = chart_items[item_index]
                    draw_chart_slot(
                        slots[slot_index],
                        chart_title,
                        chart_values,
                        placeholder="Sin datos.",
                    )
                else:
                    draw_chart_slot(
                        slots[slot_index],
                        "Espacio disponible",
                        [],
                        placeholder="Sin más gráficas.",
                    )

            draw_zero_slot(slots[3], zero_values)

    def draw_detail_tables(rows, grouping):
        groups = _group_detail_rows(rows)
        if not groups:
            return

        y = begin_page(
            "Detalle de accesos",
            f"{GROUPING_TITLES[grouping]} · {start_date} a {end_date}",
        )
        
        col_widths = [width * ratio for ratio in COLUMN_RATIOS]
        header_height = 26
        group_height = 26
        header_background = QColor("#e9edf2")
        group_background = QColor("#e2eaf5")

        def draw_group_title(name, continuation=False):
            nonlocal y
            label = f"{name}"
            if continuation:
                label += " (cont.)"
            rect = QRectF(left, y, width, group_height)
            painter.save()
            painter.setClipRect(page_rect)
            painter.fillRect(rect, group_background)
            painter.setPen(QPen(QColor("#cbd2da"), 1))
            painter.drawRect(rect)
            painter.setFont(section_font)
            painter.setPen(QColor("#25364a"))
            painter.drawText(
                rect.adjusted(6, 2, -6, -2),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                label,
            )
            painter.restore()
            y += group_height

        def draw_header_row():
            nonlocal y
            current_x = left
            for column, header in enumerate(TABLE_HEADERS):
                col_w = col_widths[column]
                rect = QRectF(current_x, y, col_w, header_height)
                _draw_cell(
                    painter,
                    rect,
                    header,
                    font=QFont("Arial", 12, QFont.Weight.Bold),
                    background=header_background,
                )
                current_x += col_w
            y += header_height

        for university, group_rows in groups:
            if y + group_height + header_height + 25 > bottom:
                y = begin_page(
                    "Detalle de accesos · continuación",
                    f"{GROUPING_TITLES[grouping]}",
                )
            draw_group_title(university)
            draw_header_row()

            for record in group_rows:
                values = (
                    _display_period(record["period"], grouping),
                    record["detail"],
                    f'{record["total"]:,}',
                )
                metrics = QFontMetrics(body_font)
                heights = []
                for column, value in enumerate(values):
                    col_w = col_widths[column]
                    bounds = metrics.boundingRect(
                        0,
                        0,
                        max(1, int(col_w - 8)),
                        4000,
                        int(Qt.AlignmentFlag.AlignLeft)
                        | int(Qt.TextFlag.TextWordWrap),
                        str(value),
                    )
                    heights.append(bounds.height())
                row_height = max(24, max(heights, default=0) + 8)

                if y + row_height > bottom:
                    y = begin_page(
                        "Detalle de accesos · continuación",
                        f"Universidad: {university}",
                    )
                    draw_group_title(university, continuation=True)
                    draw_header_row()

                painter.save()
                painter.setClipRect(page_rect)
                current_x = left
                for column, value in enumerate(values):
                    col_w = col_widths[column]
                    rect = QRectF(current_x, y, col_w, row_height)
                    _draw_cell(
                        painter,
                        rect,
                        value,
                        font=body_font,
                        background=QColor("#ffffff"),
                        align=(
                            Qt.AlignmentFlag.AlignRight
                            if column == 2
                            else Qt.AlignmentFlag.AlignLeft
                        ),
                    )
                    current_x += col_w
                painter.restore()
                y += row_height
            y += 6

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