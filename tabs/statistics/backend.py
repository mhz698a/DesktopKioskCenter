"""Consultas y exportación del generador de estadísticas."""
import csv
from PyQt6.QtCore import QObject
from css.cQDialogs import cQMsgBox
from database import Database


class StatisticsBackend(QObject):
    def __init__(self, view, database: Database, parent=None):
        super().__init__(parent)
        self.view = view
        self.database = database
        self._last_rows = []
        self.view.generate_requested.connect(self.generate_report)
        self.view.export_requested.connect(self.export_report)

    def generate_report(self):
        filters = self.view.get_report_filters()
        try:
            rows = self.database.generate_access_report(
                filters["start_date"], filters["end_date"], filters["grouping"]
            )
        except (ValueError, OSError) as exc:
            cQMsgBox.warning(self.view, "No se pudo generar el reporte", str(exc))
            return
        except Exception as exc:
            cQMsgBox.critical(
                self.view, "Error de base de datos",
                f"No se pudo consultar el historial de accesos.\n\n{exc}",
            )
            return

        formatted_rows = []
        for record in rows:
            item = dict(record)
            if filters["grouping"] == "week":
                item["period"] = f"Semana del {item['period']}"
            formatted_rows.append(item)
        self._last_rows = formatted_rows
        total = sum(int(item.get("total", 0)) for item in formatted_rows)
        self.view.set_report_rows(formatted_rows, total)

    def export_report(self):
        if not self._last_rows:
            cQMsgBox.information(
                self.view, "Sin datos",
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
                writer.writerow(["Periodo", "Procedencia", "Universidad / origen", "Accesos"])
                for row in self._last_rows:
                    writer.writerow([
                        row.get("period", ""), row.get("origin", ""),
                        row.get("source", ""), row.get("total", 0),
                    ])
        except OSError as exc:
            cQMsgBox.critical(
                self.view, "Error al exportar",
                f"No se pudo guardar el CSV.\n\n{exc}",
            )
            return
        cQMsgBox.information(
            self.view, "Reporte exportado", f"El archivo se guardó en:\n{path}"
        )
