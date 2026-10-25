"""Interfaz de la pestaña Inicios Recibidos; solo dibuja datos que recibe del backend."""
from PyQt6.QtWidgets import QHeaderView, QVBoxLayout, QWidget, QTableWidgetItem

from css.cQDialogs import cQMsgBox
from css.cQTablewidget import cQTableW
from css.cqtoolbar import cQToolbar
from PyQt6.QtCore import pyqtSignal


class ReceivedLoginsTab(QWidget):
    count_totals_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        toolbar = cQToolbar("Inicios Recibidos", self)
        toolbar.setMovable(False)
        count_action = toolbar.addAction("Contar Totales")
        count_action.triggered.connect(
            lambda _checked=False: self.count_totals_requested.emit()
        )

        self.table = cQTableW(0, 9, self)
        self.table.setHorizontalHeaderLabels(
            [
                "Índice",
                "Fecha y hora",
                "Equipo",
                "IP cliente",
                "Identificador",
                "Tipo de usuario",
                "Acción",
                "Resultado",
                "Mensaje",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        layout.addWidget(toolbar)
        layout.addWidget(self.table)

    def set_records(self, records):
        """Muestra los eventos recibidos; el id de SQLite sirve como índice visible."""
        self.table.setRowCount(0)
        for row, record in enumerate(records):
            self.table.insertRow(row)
            values = (
                str(record.get("id", "")),
                record.get("received_at", ""),
                record.get("kiosk_name", ""),
                record.get("client_ip", ""),
                record.get("identifier", ""),
                record.get("user_type", ""),
                record.get("action", ""),
                record.get("result", ""),
                record.get("message", ""),
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value or "")))
