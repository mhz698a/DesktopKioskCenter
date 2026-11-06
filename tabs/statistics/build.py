"""Interfaz del generador de reportes con pestañas de procedencia y exportación."""
from pathlib import Path

from PyQt6.QtCore import QDate, Qt, pyqtSignal, QStandardPaths
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from css.cQTablewidget import cQTableW
from css.cqtoolbar import cQToolbar
from tabs.statistics.charts import BarChartWidget


class PdfExportOptionsDialog(QDialog):
    """Opciones de periodos, destino y apertura posterior del PDF."""

    def __init__(self, start_date, end_date, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exportar reporte a PDF")
        self.setMinimumWidth(510)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"Rango de fechas: {start_date} a {end_date}",
            self,
        ))
        layout.addWidget(QLabel(
            "Selecciona uno o varios periodos para incluir en el documento:",
            self,
        ))

        periods_layout = QHBoxLayout()
        self.day_checkbox = QCheckBox("Por día", self)
        self.week_checkbox = QCheckBox("Por semana", self)
        self.month_checkbox = QCheckBox("Por mes", self)
        for checkbox in (
            self.day_checkbox,
            self.week_checkbox,
            self.month_checkbox,
        ):
            checkbox.setChecked(True)
            periods_layout.addWidget(checkbox)
        layout.addLayout(periods_layout)

        path_form = QFormLayout()
        path_row = QHBoxLayout()
        documents = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        if not documents:
            documents = str(Path.home())
        default_path = str(Path(documents) / "Reporte_Accesos.pdf")

        self.path_edit = QLineEdit(default_path, self)
        self.path_edit.setClearButtonEnabled(True)
        self.browse_button = QPushButton("Examinar...", self)
        self.browse_button.clicked.connect(self._browse_destination)
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(self.browse_button)
        path_form.addRow("Guardar en:", path_row)
        layout.addLayout(path_form)

        self.open_after_export_checkbox = QCheckBox(
            "Abrir el PDF al terminar la exportación",
            self,
        )
        self.open_after_export_checkbox.setChecked(False)
        layout.addWidget(self.open_after_export_checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Exportar PDF")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_destination(self):
        filename, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Guardar reporte PDF",
            self.path_edit.text().strip() or "Reporte_Accesos.pdf",
            "Documento PDF (*.pdf)",
        )
        # Cancelar la selección de destino cancela todo el flujo de exportación.
        if not filename:
            self.reject()
            return
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"
        self.path_edit.setText(filename)

    def accept(self):
        if not any((
            self.day_checkbox.isChecked(),
            self.week_checkbox.isChecked(),
            self.month_checkbox.isChecked(),
        )):
            QMessageBox.warning(
                self,
                "Selecciona un periodo",
                "Debes seleccionar al menos un periodo para generar el PDF.",
            )
            return

        destination = self.path_edit.text().strip()
        if not destination:
            QMessageBox.warning(
                self,
                "Destino requerido",
                "Selecciona la ubicación y el nombre del archivo PDF.",
            )
            return

        if not destination.lower().endswith(".pdf"):
            destination += ".pdf"
        self.path_edit.setText(destination)
        super().accept()

    def get_options(self):
        periods = []
        if self.day_checkbox.isChecked():
            periods.append("day")
        if self.week_checkbox.isChecked():
            periods.append("week")
        if self.month_checkbox.isChecked():
            periods.append("month")
        return {
            "groupings": periods,
            "filename": self.path_edit.text().strip(),
            "open_after_export": self.open_after_export_checkbox.isChecked(),
        }


class StatisticsTab(QWidget):
    generate_requested = pyqtSignal()
    export_requested = pyqtSignal()
    export_charts_requested = pyqtSignal()
    export_pdf_requested = pyqtSignal()

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
        self.export_pdf_button = QPushButton("Exportar PDF", self)
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
        self.export_pdf_button.clicked.connect(
            lambda _checked=False: self.export_pdf_requested.emit()
        )

        filters.addWidget(QLabel("Agrupar tabla:", self))
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
        filters.addWidget(self.export_pdf_button)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)

        report_panel = QWidget(splitter)
        report_layout = QVBoxLayout(report_panel)
        report_layout.setContentsMargins(0, 0, 6, 0)
        self.total_label = QLabel("Total de accesos: 0", report_panel)
        self.table = cQTableW(0, 4, report_panel)
        self.table.setHorizontalHeaderLabels(
            ["Periodo", "Procedencia", "Universidad / facultad", "Accesos"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        report_layout.addWidget(self.total_label)
        report_layout.addWidget(self.table, 1)

        self.charts_panel = QTabWidget(splitter)
        self.charts_panel.setMinimumWidth(340)

        general_page = QWidget(self.charts_panel)
        general_layout = QVBoxLayout(general_page)
        general_layout.setContentsMargins(6, 6, 6, 6)
        general_layout.setSpacing(10)
        general_layout.addWidget(QLabel(
            "Evolución temporal y procedencia agrupada por institución.",
            general_page,
        ))
        self.access_chart = BarChartWidget(
            "Accesos por periodo", horizontal=False, parent=general_page
        )
        self.general_origin_chart = BarChartWidget(
            "Procedencia general (UAQ consolidada)",
            horizontal=True,
            parent=general_page,
        )
        general_layout.addWidget(self.access_chart, 1)
        general_layout.addWidget(self.general_origin_chart, 1)
        self.charts_panel.addTab(general_page, "Procedencia General")

        faculties_page = QWidget(self.charts_panel)
        faculties_layout = QVBoxLayout(faculties_page)
        faculties_layout.setContentsMargins(6, 6, 6, 6)
        faculties_layout.addWidget(QLabel(
            "Accesos de alumnos internos distribuidos por facultad de la "
            "Universidad Autónoma de Querétaro.",
            faculties_page,
        ))
        self.faculty_chart = BarChartWidget(
            "Accesos por facultad UAQ",
            horizontal=True,
            parent=faculties_page,
        )
        faculties_layout.addWidget(self.faculty_chart, 1)
        self.charts_panel.addTab(faculties_page, "Procedencia Facultades")

        splitter.addWidget(report_panel)
        splitter.addWidget(self.charts_panel)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([700, 410])

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

    def set_chart_data(self, period_totals, general_origins, faculties):
        self.access_chart.set_data(period_totals)
        self.general_origin_chart.set_data(general_origins)
        self.faculty_chart.set_data(faculties)

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

    def choose_pdf_export_options(self):
        filters = self.get_report_filters()
        dialog = PdfExportOptionsDialog(
            filters["start_date"],
            filters["end_date"],
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog.get_options()

    def save_chart_images(self, filename):
        """Guarda el panel y las tres gráficas en archivos PNG independientes."""
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
                self.general_origin_chart,
                base_path.with_name(base_path.stem + "_procedencia_general.png"),
            ),
            (
                self.faculty_chart,
                base_path.with_name(base_path.stem + "_procedencia_facultades.png"),
            ),
        )
        saved = []
        for widget, target in targets:
            if widget.grab().save(str(target), "PNG"):
                saved.append(str(target))
        return saved
