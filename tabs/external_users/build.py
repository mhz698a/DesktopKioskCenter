from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)


class ExternalUsersTab(QWidget):
    add_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        toolbar = QToolBar("Usuarios Externos Registrados", self)
        toolbar.setMovable(False)
        add_action = toolbar.addAction("Agregar Usuario")
        add_action.triggered.connect(lambda _checked=False: self.add_requested.emit())

        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(
            [
                "Índice",
                "Nombres",
                "Apellidos",
                "Tipo de usuario",
                "Universidad Perteneciente",
            ]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        layout.addWidget(toolbar)
        layout.addWidget(self.table)

    def set_records(self, records):
        self.table.setRowCount(0)
        for row, record in enumerate(records, start=1):
            self.table.insertRow(row - 1)
            values = (
                str(row),
                record.get("nombres", ""),
                record.get("apellidos", ""),
                record.get("tipo_usuario", ""),
                record.get("universidad", ""),
            )
            for column, value in enumerate(values):
                self.table.setItem(row - 1, column, QTableWidgetItem(value))
