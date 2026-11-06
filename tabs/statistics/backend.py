"""Consultas y exportación del generador de estadísticas."""
import csv

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QObject

from css.cQDialogs import cQMsgBox
from database import Database
from tabs.statistics.pdf_export import export_statistics_pdf
from tabs.statistics.report_data import build_chart_data


class StatisticsBackend(QObject):
    def __init__(self, view, database: Database, parent=None):
        super().__init__(parent)
        self.view = view
        self.database = database
        self._last_rows = []
        self.view.generate_requested.connect(self.generate_report)
        self.view.export_requested.connect(self.export_report)
        self.view.export_charts_requested.connect(self.export_charts)
        self.view.export_pdf_requested.connect(self.export_pdf)

    def generate_report(self):
        filters = self.view.get_report_filters()
        grouping = filters["grouping"]
        try:
            rows = self.database.generate_access_report(
                filters["start_date"],
                filters["end_date"],
                grouping,
            )
        except (ValueError, OSError) as exc:
            cQMsgBox.warning(self.view, "No se pudo generar el reporte", str(exc))
            return
        except Exception as exc:
            cQMsgBox.critical(
                self.view,
                "Error de base de datos",
                f"No se pudo consultar el historial de accesos.\n\n{exc}",
            )
            return

        period_chart_data, general_data, faculty_data = build_chart_data(
            rows, grouping
        )
        formatted_rows = []
        for record in rows:
            item = dict(record)
            if grouping == "week":
                item["period"] = f"Semana del {item['period']}"
            formatted_rows.append(item)

        self._last_rows = formatted_rows
        total = sum(int(item.get("total", 0)) for item in formatted_rows)
        self.view.set_report_rows(formatted_rows, total)
        self.view.set_chart_data(
            period_chart_data,
            general_data,
            faculty_data,
        )

    def export_pdf(self):
        options = self.view.choose_pdf_export_options()
        # Rechazar o cancelar el diálogo de opciones/destino cancela toda la acción.
        if options is None:
            return

        filters = self.view.get_report_filters()
        reports = {}
        try:
            for grouping in options["groupings"]:
                reports[grouping] = self.database.generate_access_report(
                    filters["start_date"],
                    filters["end_date"],
                    grouping,
                )
        except (ValueError, OSError) as exc:
            cQMsgBox.warning(
                self.view,
                "No se pudo consultar el reporte",
                str(exc),
            )
            return
        except Exception as exc:
            cQMsgBox.critical(
                self.view,
                "Error de base de datos",
                f"No se pudieron consultar los periodos seleccionados.\n\n{exc}",
            )
            return

        total = sum(
            int(row.get("total", 0))
            for period_rows in reports.values()
            for row in period_rows
        )
        if total <= 0:
            cQMsgBox.information(
                self.view,
                "Sin accesos",
                "No existen accesos en el rango de fechas y periodos seleccionados.",
            )
            return

        try:
            output_path = export_statistics_pdf(
                options["filename"],
                start_date=filters["start_date"],
                end_date=filters["end_date"],
                reports=reports,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            cQMsgBox.critical(
                self.view,
                "Error al exportar PDF",
                f"No se pudo generar el documento.\n\n{exc}",
            )
            return
        except Exception as exc:
            cQMsgBox.critical(
                self.view,
                "Error al exportar PDF",
                f"Ocurrió un error inesperado al preparar el documento.\n\n{exc}",
            )
            return

        cQMsgBox.information(
            self.view,
            "Reporte PDF generado",
            f"El reporte se guardó en:\n{output_path}",
        )

        if options["open_after_export"]:
            opened = QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(output_path))
            )
            if not opened:
                cQMsgBox.warning(
                    self.view,
                    "No se pudo abrir el PDF",
                    "El reporte se generó correctamente, pero Windows no pudo "
                    "abrirlo con la aplicación predeterminada.",
                )

    def export_charts(self):
        if not self._last_rows:
            cQMsgBox.information(
                self.view,
                "Sin datos",
                "Genera un reporte antes de exportar las gráficas.",
            )
            return

        path = self.view.choose_chart_export_path()
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"

        try:
            saved_files = self.view.save_chart_images(path)
        except (OSError, RuntimeError) as exc:
            cQMsgBox.critical(
                self.view,
                "Error al exportar gráficas",
                f"No se pudieron generar las imágenes PNG.\n\n{exc}",
            )
            return

        if len(saved_files) != 4:
            cQMsgBox.critical(
                self.view,
                "Exportación incompleta",
                "No se pudieron guardar todas las imágenes del reporte. "
                f"Se guardaron {len(saved_files)} de 4.",
            )
            return

        cQMsgBox.information(
            self.view,
            "Gráficas exportadas",
            "Se guardaron estas imágenes PNG:\n\n"
            + "\n".join(saved_files),
        )

    def export_report(self):
        if not self._last_rows:
            cQMsgBox.information(
                self.view,
                "Sin datos",
                "Genera un reporte con resultados antes de exportar.",
            )
            return
        path = self.view.choose_export_path()
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as output:
                writer = csv.writer(output)
                writer.writerow([
                    "Periodo", "Procedencia", "Universidad / facultad", "Accesos"
                ])
                for row in self._last_rows:
                    writer.writerow([
                        row.get("period", ""),
                        row.get("origin", ""),
                        row.get("source", ""),
                        row.get("total", 0),
                    ])
        except OSError as exc:
            cQMsgBox.critical(
                self.view,
                "Error al exportar",
                f"No se pudo guardar el CSV.\n\n{exc}",
            )
            return
        cQMsgBox.information(
            self.view,
            "Reporte exportado",
            f"El archivo se guardó en:\n{path}",
        )
