from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QSplitter,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from css.cqtoolbar import cQToolbar
from css.cQTablewidget import cQTableW
from tabs.registered_user_editor import RegisteredUserEditor


class InternalStaffTab(QWidget):
    add_requested = pyqtSignal()
    faculty_catalog_requested = pyqtSignal()
    record_selection_changed = pyqtSignal(int)
    save_requested = pyqtSignal()
    delete_requested = pyqtSignal()
    revert_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        toolbar = cQToolbar("Docentes y administrativos registrados", self)

        add_action = toolbar.addAction("Agregar personal")
        add_action.triggered.connect(
            lambda _checked=False: self.add_requested.emit()
        )
        faculty_action = toolbar.addAction("Administrar facultades")
        faculty_action.triggered.connect(
            lambda _checked=False: self.faculty_catalog_requested.emit()
        )

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.table = cQTableW(0, 7, splitter)
        self.table.setHorizontalHeaderLabels([
            "Índice", "Tipo", "Nombres", "Apellidos", "Email",
            "Facultad", "No. de empleado",
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

        self.editor_panel = RegisteredUserEditor("staff", splitter)
        self.editor_panel.save_requested.connect(self.save_requested.emit)
        self.editor_panel.delete_requested.connect(self.delete_requested.emit)
        self.editor_panel.revert_requested.connect(self.revert_requested.emit)

        splitter.addWidget(self.table)
        splitter.addWidget(self.editor_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([700, 420])

        layout.addWidget(toolbar)
        layout.addWidget(splitter)

    def _on_selection_changed(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.record_selection_changed.emit(-1)
            return
        item = self.table.item(rows[0].row(), 0)
        record_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        self.record_selection_changed.emit(
            int(record_id) if record_id is not None else -1
        )

    def set_records(self, records, selected_id=None, emit_selection=True):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        selected_row = None
        for row, record in enumerate(records):
            self.table.insertRow(row)
            item = QTableWidgetItem(str(row + 1))
            item.setData(Qt.ItemDataRole.UserRole, int(record["id"]))
            self.table.setItem(row, 0, item)
            values = (
                record.get("tipo_usuario", ""),
                record.get("nombres", ""),
                record.get("apellidos", ""),
                record.get("email", ""),
                record.get("facultad", ""),
                record.get("numero_empleado", ""),
            )
            for column, value in enumerate(values, start=1):
                self.table.setItem(
                    row, column, QTableWidgetItem(str(value or ""))
                )
            if selected_id is not None and int(record["id"]) == int(selected_id):
                selected_row = row

        if selected_row is not None:
            self.table.selectRow(selected_row)
        else:
            self.table.clearSelection()
        self.table.blockSignals(False)

        if emit_selection:
            self.record_selection_changed.emit(
                int(selected_id) if selected_row is not None else -1
            )
