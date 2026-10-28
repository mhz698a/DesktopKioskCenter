"""Interfaz de la tabla Logs de accesos."""
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHeaderView, QTableWidgetItem, QVBoxLayout, QWidget

from css.cQTablewidget import cQTableW
from css.cqtoolbar import cQToolbar


class AccessLogsTab(QWidget):
    count_totals_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        toolbar = cQToolbar("Logs de accesos", self)
        count_action = toolbar.addAction("Contar totales")
        count_action.triggered.connect(lambda _checked=False: self.count_totals_requested.emit())
        self.table = cQTableW(0, 9, self)
        self.table.setHorizontalHeaderLabels([
            "Índice", "Fecha Hora de Acceso", "Equipo", "Nombres", "Apellidos",
            "Expediente", "Facultad", "Universidad Externa", "Tipo de Usuario",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(toolbar)
        layout.addWidget(self.table)

    def set_records(self, records):
        self.table.setRowCount(0)
        for row, record in enumerate(records):
            self.table.insertRow(row)
            values = (
                str(record.get("id", row + 1)), record.get("accessed_at", ""),
                record.get("kiosk_name", ""), record.get("nombres", ""),
                record.get("apellidos", ""), record.get("expediente", ""),
                record.get("facultad", ""), record.get("universidad_externa", ""),
                record.get("tipo_usuario", ""),
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value or "")))
