"""Interfaz del generador de reportes con gráficas en un panel lateral."""
from pathlib import Path

from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QDateEdit, QFileDialog, QHBoxLayout, QLabel, QPushButton,
    QSplitter, QTableWidgetItem, QVBoxLayout, QWidget,
)

from css.cQTablewidget import cQTableW
from css.cqtoolbar import cQToolbar
from tabs.statistics.charts import BarChartWidget


class StatisticsTab(QWidget):
    generate_requested = pyqtSignal()
    export_requested = pyqtSignal()
    export_charts_requested = pyqtSignal()

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
        self.export_charts_button = QPushButton("Exportar gráficas PNG", self)
        self.export_button.setEnabled(False)
        self.export_charts_button.setEnabled(False)

        self.generate_button.clicked.connect(
            lambda _checked=False: self.generate_requested.emit()
        )
        self.export_button.clicked.connect(
            lambda _checked=False: self.export_requested.emit()
        )
        self.export_charts_button.clicked.connect(
            lambda _checked=False: self.export_charts_requested.emit()
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
        filters.addWidget(self.export_charts_button)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)

        report_panel = QWidget(splitter)
        report_layout = QVBoxLayout(report_panel)
        report_layout.setContentsMargins(0, 0, 6, 0)
        self.total_label = QLabel("Total de accesos: 0", report_panel)
        self.table = cQTableW(0, 4, report_panel)
        self.table.setHorizontalHeaderLabels(
            ["Periodo", "Procedencia", "Universidad / origen", "Accesos"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        report_layout.addWidget(self.total_label)
        report_layout.addWidget(self.table, 1)

        self.charts_panel = QWidget(splitter)
        self.charts_panel.setMinimumWidth(320)
        charts_layout = QVBoxLayout(self.charts_panel)
        charts_layout.setContentsMargins(6, 0, 0, 0)
        charts_layout.setSpacing(10)

        charts_heading = QLabel("Visualización del reporte", self.charts_panel)
        charts_heading.setObjectName("statisticsChartsHeading")
        self.access_chart = BarChartWidget(
            "Accesos por periodo", horizontal=False, parent=self.charts_panel
        )
        self.origin_chart = BarChartWidget(
            "Procedencia (universidades y público general)",
            horizontal=True,
            parent=self.charts_panel,
        )

        charts_layout.addWidget(charts_heading)
        charts_layout.addWidget(self.access_chart, 1)
        charts_layout.addWidget(self.origin_chart, 1)

        splitter.addWidget(report_panel)
        splitter.addWidget(self.charts_panel)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([700, 390])

        layout.addWidget(toolbar)
        layout.addLayout(filters)
        layout.addWidget(splitter, 1)

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
                record.get("period", ""),
                record.get("origin", ""),
                record.get("source", ""),
                str(record.get("total", 0)),
            )
            for column, value in enumerate(values):
                self.table.setItem(
                    row_index, column, QTableWidgetItem(str(value or ""))
                )
        self.total_label.setText(f"Total de accesos: {int(total)}")
        self.export_button.setEnabled(bool(rows))
        self.export_charts_button.setEnabled(bool(rows))

    def set_chart_data(self, period_totals, source_totals):
        self.access_chart.set_data(period_totals)
        self.origin_chart.set_data(source_totals)

    def choose_export_path(self):
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Exportar reporte de accesos",
            "reporte_accesos.csv",
            "Archivos CSV (*.csv)",
        )
        return path

    def choose_chart_export_path(self):
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Exportar gráficas del reporte",
            "reporte_graficas.png",
            "Imagen PNG (*.png)",
        )
        return path

    def save_chart_images(self, filename):
        """Guarda el panel compuesto y cada gráfica en PNG."""
        base_path = Path(filename)
        if base_path.suffix.lower() != ".png":
            base_path = base_path.with_suffix(".png")

        targets = (
            (self.charts_panel, base_path),
            (
                self.access_chart,
                base_path.with_name(base_path.stem + "_accesos.png"),
            ),
            (
                self.origin_chart,
                base_path.with_name(base_path.stem + "_procedencia.png"),
            ),
        )
        saved = []
        for widget, target in targets:
            if widget.grab().save(str(target), "PNG"):
                saved.append(str(target))
        return saved
