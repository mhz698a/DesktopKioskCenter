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
        self.view.export_charts_requested.connect(self.export_charts)

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
        period_totals = {}
        source_totals = {}
        for item in formatted_rows:
            period = str(item.get("period", ""))
            value = int(item.get("total", 0))
            period_totals[period] = period_totals.get(period, 0) + value
            source = str(item.get("source") or item.get("origin") or "Sin clasificar")
            source_totals[source] = source_totals.get(source, 0) + value

        period_chart_data = []
        for period, value in sorted(period_totals.items()):
            raw_period = (
                period.removeprefix("Semana del ")
                if grouping == "week" else period
            )
            if grouping == "day":
                label = raw_period[8:10] + "/" + raw_period[5:7]
            elif grouping == "week":
                label = "Sem " + raw_period[8:10] + "/" + raw_period[5:7]
            else:
                label = raw_period[5:7] + "/" + raw_period[:4]
            period_chart_data.append((label, value))

        source_chart_data = sorted(
            source_totals.items(), key=lambda item: item[1], reverse=True
        )
        self._last_rows = formatted_rows
        total = sum(int(item.get("total", 0)) for item in formatted_rows)
        self.view.set_report_rows(formatted_rows, total)
        self.view.set_chart_data(period_chart_data, source_chart_data)

    def export_charts(self):
        if not self._last_rows:
            cQMsgBox.information(
                self.view, "Sin datos",
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
                self.view, "Error al exportar gráficas",
                f"No se pudieron generar las imágenes PNG.\\n\\n{exc}",
            )
            return

        if len(saved_files) != 3:
            cQMsgBox.critical(
                self.view, "Exportación incompleta",
                "No se pudieron guardar todas las imágenes del reporte. "
                f"Se guardaron {len(saved_files)} de 3.",
            )
            return

        cQMsgBox.information(
            self.view,
            "Gráficas exportadas",
            "Se guardaron estas imágenes PNG:\\n\\n" + "\\n".join(saved_files),
        )

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
