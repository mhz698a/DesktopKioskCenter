"""Backend de la pestaña Logs de peticiones; todas las lecturas usan Database/SQLite."""
from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QWidget

from css.cQDialogs import cQMsgBox
from database import Database


class ReceivedLoginsBackend(QObject):
    def __init__(self, view, database: Database, parent=None):
        super().__init__(parent)
        self.view = view
        self.database = database
        self._last_records = None
        self.view.count_totals_requested.connect(self.count_totals)
        self.refresh()

    def refresh(self):
        """Refresca los últimos eventos recibidos desde SQLite."""
        records = self.database.list_received_logins()
        if records != self._last_records:
            self.view.set_records(records)
            self._last_records = records

    def count_totals(self):
        """Cuenta en SQL y presenta el total más los subtotales por tipo/resultado."""
        try:
            summary = self.database.count_received_logins()
            self.refresh()
        except Exception as exc:
            cQMsgBox.critical(
                self.view,
                "Error de base de datos",
                f"No se pudieron contar los logs de peticiones.\n\n{exc}",
            )
            return

        lines = [f"Total de logs de peticiones: {summary['total']}"]

        if summary["by_type"]:
            lines.append("")
            lines.append("Por tipo de usuario:")
            lines.extend(
                f"  • {item['label']}: {item['total']}"
                for item in summary["by_type"]
            )

        if summary["by_result"]:
            lines.append("")
            lines.append("Por resultado:")
            lines.extend(
                f"  • {item['label']}: {item['total']}"
                for item in summary["by_result"]
            )

        cQMsgBox.information(
            self.view,
            "Totales de logs de peticiones",
            "\n".join(lines),
        )
