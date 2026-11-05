"""Interfaz del generador de reportes de accesos."""
from PyQt6.QtCore import QDate, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QDateEdit, QFileDialog, QHBoxLayout, QLabel, QPushButton,
    QTableWidgetItem, QVBoxLayout, QWidget,
)
from css.cQTablewidget import cQTableW
from css.cqtoolbar import cQToolbar


class StatisticsTab(QWidget):
    generate_requested = pyqtSignal()
    export_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        toolbar = cQToolbar("Estadísticas", self)
        filters = QHBoxLayout()

        self.grouping_combo = QComboBox(self)
        self.grouping_combo.addItem("Por día", "day")
        self.grouping_combo.addItem("Por semana", "week")
        self.grouping_combo.addItem("Por mes", "month")

        self.start_date = QDateEdit(self)
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("dd/MM/yyyy")
        self.start_date.setDate(QDate.currentDate().addDays(-29))
        self.end_date = QDateEdit(self)
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("dd/MM/yyyy")
        self.end_date.setDate(QDate.currentDate())

        self.generate_button = QPushButton("Generar reporte", self)
        self.export_button = QPushButton("Exportar CSV", self)
        self.export_button.setEnabled(False)
        self.generate_button.clicked.connect(
            lambda _checked=False: self.generate_requested.emit()
        )
        self.export_button.clicked.connect(
            lambda _checked=False: self.export_requested.emit()
        )

        filters.addWidget(QLabel("Agrupar accesos:", self))
        filters.addWidget(self.grouping_combo)
        filters.addSpacing(12)
        filters.addWidget(QLabel("Desde:", self))
        filters.addWidget(self.start_date)
        filters.addWidget(QLabel("Hasta:", self))
        filters.addWidget(self.end_date)
        filters.addStretch(1)
        filters.addWidget(self.generate_button)
        filters.addWidget(self.export_button)

        self.total_label = QLabel("Total de accesos: 0", self)
        self.table = cQTableW(0, 4, self)
        self.table.setHorizontalHeaderLabels(
            ["Periodo", "Procedencia", "Universidad / origen", "Accesos"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(toolbar)
        layout.addLayout(filters)
        layout.addWidget(self.total_label)
        layout.addWidget(self.table, 1)

    def get_report_filters(self):
        return {
            "start_date": self.start_date.date().toString("yyyy-MM-dd"),
            "end_date": self.end_date.date().toString("yyyy-MM-dd"),
            "grouping": str(self.grouping_combo.currentData()),
        }

    def set_report_rows(self, rows, total):
        self.table.setRowCount(0)
        for row_index, record in enumerate(rows):
            self.table.insertRow(row_index)
            values = (
                record.get("period", ""), record.get("origin", ""),
                record.get("source", ""), str(record.get("total", 0)),
            )
            for column, value in enumerate(values):
                self.table.setItem(
                    row_index, column, QTableWidgetItem(str(value or ""))
                )
        self.total_label.setText(f"Total de accesos: {int(total)}")
        self.export_button.setEnabled(bool(rows))

    def choose_export_path(self):
        path, _selected_filter = QFileDialog.getSaveFileName(
            self, "Exportar reporte de accesos", "reporte_accesos.csv",
            "Archivos CSV (*.csv)",
        )
        return path
