"""Exportación de reportes de estadísticas a PDF con gráficas embebidas."""
from __future__ import annotations

from html import escape
from pathlib import Path

from PyQt6.QtCore import QMarginsF, Qt, QUrl
from PyQt6.QtGui import (
    QFont,
    QImage,
    QPageLayout,
    QPageSize,
    QPainter,
    QPdfWriter,
    QTextDocument,
)

from tabs.statistics.charts import BarChartWidget
from tabs.statistics.report_data import build_chart_data


GROUPING_TITLES = {
    "day": "Accesos por día",
    "week": "Accesos por semana",
    "month": "Accesos por mes",
}


def _chart_image(title, values, *, horizontal=False):
    """Renderiza una gráfica Qt a QImage sin mostrar una ventana adicional."""
    chart = BarChartWidget(title, horizontal=horizontal)
    chart.resize(1100 if horizontal else 900, 340)
    chart.set_data(values)
    chart.ensurePolished()

    image = QImage(
        chart.size(),
        QImage.Format.Format_ARGB32_Premultiplied,
    )
    image.fill(Qt.GlobalColor.white)

    painter = QPainter(image)
    try:
        chart.render(painter)
    finally:
        painter.end()
        chart.close()
        chart.deleteLater()

    return image


def _table_html(rows):
    body = []
    for row in rows:
        period = escape(str(row.get("period", "")))
        raw_origin = str(row.get("origin", ""))
        origin_label = (
            "Universidad Autónoma de Querétaro"
            if raw_origin == "UAQ" else raw_origin
        )
        origin = escape(origin_label)
        source = escape(str(row.get("source", "")))
        total = int(row.get("total", 0))
        body.append(
            "<tr>"
            f"<td>{period}</td><td>{origin}</td>"
            f"<td>{source}</td><td class='number'>{total:,}</td>"
            "</tr>"
        )

    return (
        "<table><thead><tr>"
        "<th>Periodo</th><th>Procedencia general</th>"
        "<th>Detalle / facultad</th><th>Accesos</th>"
        "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table>"
    )


def export_statistics_pdf(
    filename,
    *,
    start_date,
    end_date,
    reports,
):
    """Crea un PDF con una sección por agrupación seleccionada.

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

    document = QTextDocument()
    document.setDefaultFont(QFont("Arial", 9))
    document.setDocumentMargin(0)

    html_sections = [
        """
        <html><head><meta charset="utf-8">
        <style>
            body { font-family: Arial; color: #20242b; font-size: 9pt; }
            h1 { font-size: 19pt; margin: 0 0 5pt 0; }
            h2 { font-size: 15pt; margin: 18pt 0 6pt 0; color: #25364a; }
            h3 { font-size: 11pt; margin: 12pt 0 5pt 0; }
            p.meta { color: #596575; margin: 0 0 12pt 0; }
            p.total { font-size: 11pt; font-weight: bold; margin: 6pt 0 10pt 0; }
            table { border-collapse: collapse; table-layout: fixed; width: 100%; font-size: 8pt; }
            th { background-color: #e9edf2; text-align: left; }
            th, td { width: 25%; border: 1px solid #cbd2da; padding: 4pt; word-wrap: break-word; }
            td.number { text-align: right; }
            img.chart { width: 100%; }
            .section-break { height: 10pt; }
        </style></head><body>
        """,
        "<h1>Reporte de accesos</h1>",
        (
            "<p class='meta'>Periodo consultado: "
            f"{escape(str(start_date))} a {escape(str(end_date))}</p>"
        ),
    ]

    image_resources = []
    for index, (grouping, rows) in enumerate(selected_reports):
        period_data, general_data, faculty_data = build_chart_data(rows, grouping)
        total = sum(int(row.get("total", 0)) for row in rows)

        trend_url = QUrl(f"report-image:///{grouping}-trend")
        general_url = QUrl(f"report-image:///{grouping}-general")
        faculty_url = QUrl(f"report-image:///{grouping}-faculties")

        images = (
            (
                trend_url,
                _chart_image(
                    "Accesos por periodo",
                    period_data,
                    horizontal=False,
                ),
            ),
            (
                general_url,
                _chart_image(
                    "Procedencia general",
                    general_data,
                    horizontal=True,
                ),
            ),
            (
                faculty_url,
                _chart_image(
                    "Accesos por facultad",
                    faculty_data,
                    horizontal=True,
                ),
            ),
        )
        image_resources.extend(images)

        if index:
            html_sections.append("<div class='section-break'></div><hr>")

        html_sections.extend([
            f"<h2>{escape(GROUPING_TITLES[grouping])}</h2>",
            f"<p class='total'>Total de accesos: {total:,}</p>",
            "<h3>Accesos por periodo</h3>",
            f"<img class='chart' src='{escape(trend_url.toString())}'>",
            "<h3>Procedencia general</h3>",
            f"<img class='chart' src='{escape(general_url.toString())}'>",
            "<h3>Procedencia por facultad UAQ</h3>",
            f"<img class='chart' src='{escape(faculty_url.toString())}'>",
            "<h3>Detalle de accesos</h3>",
            _table_html(rows),
        ])

    html_sections.append("</body></html>")

    for url, image in image_resources:
        document.addResource(
            QTextDocument.ResourceType.ImageResource,
            url,
            image,
        )

    document.setHtml("".join(html_sections))

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
    document.setPageSize(
        writer.pageLayout().paintRect(QPageLayout.Unit.Point).size()
    )
    document.print(writer)

    if not output_path.is_file() or output_path.stat().st_size < 5:
        raise OSError("Qt no pudo generar el archivo PDF solicitado.")

    with output_path.open("rb") as pdf_file:
        if pdf_file.read(5) != b"%PDF-":
            raise OSError("Qt generó un archivo, pero no tiene una cabecera PDF válida.")

    return output_path
