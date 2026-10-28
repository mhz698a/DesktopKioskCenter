"""Backend de la pestaña Logs de accesos."""
from PyQt6.QtCore import QObject

from css.cQDialogs import cQMsgBox
from database import Database


class AccessLogsBackend(QObject):
    def __init__(self, view, database: Database, parent=None):
        super().__init__(parent)
        self.view = view
        self.database = database
        self._last_records = None
        self.view.count_totals_requested.connect(self.count_totals)
        self.refresh()

    def refresh(self):
        records = self.database.list_access_logs()
        if records != self._last_records:
            self.view.set_records(records)
            self._last_records = records

    def count_totals(self):
        try:
            summary = self.database.count_access_logs()
            self.refresh()
        except Exception as exc:
            cQMsgBox.critical(self.view, "Error de base de datos", f"No se pudieron contar los logs de accesos.\n\n{exc}")
            return
        lines = [f"Total de accesos: {summary['total']}"]
        if summary["by_type"]:
            lines.extend(["", "Por tipo de usuario:"])
            lines.extend(f"  • {item['label']}: {item['total']}" for item in summary["by_type"])
        if summary["by_kiosk"]:
            lines.extend(["", "Por equipo:"])
            lines.extend(f"  • {item['label']}: {item['total']}" for item in summary["by_kiosk"])
        cQMsgBox.information(self.view, "Totales de accesos", "\n".join(lines))
