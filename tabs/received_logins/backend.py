"""Backend de la pestaña Inicios Recibidos; todas las lecturas usan Database/SQLite."""
from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QWidget

from css.cQDialogs import cQMsgBox
from database import Database


class ReceivedLoginsBackend(QObject):
    def __init__(self, view, database: Database, parent=None):
        super().__init__(parent)
        self.view = view
        self.database = database
        self.view.count_totals_requested.connect(self.count_totals)
        self.refresh()

    def refresh(self):
        """Vuelve a consultar los últimos eventos en SQLite."""
        self.view.set_records(self.database.list_received_logins())

    def count_totals(self):
        """Cuenta en SQL y presenta el total más los subtotales por tipo/resultado."""
        try:
            summary = self.database.count_received_logins()
            self.refresh()
        except Exception as exc:
            cQMsgBox.critical(
                self.view,
                "Error de base de datos",
                f"No se pudieron contar los inicios recibidos.\n\n{exc}",
            )
            return

        lines = [f"Total de inicios recibidos: {summary['total']}"]

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
            "Totales de inicios recibidos",
            "\n".join(lines),
        )
