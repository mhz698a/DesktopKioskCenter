from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QHeaderView, QHBoxLayout, QLabel,
    QPushButton, QSplitter, QTableWidgetItem, QVBoxLayout, QWidget,
)

from css.cqtoolbar import cQToolbar
from css.cQTablewidget import cQTableW
from tabs.registered_user_editor import RegisteredUserEditor


class InternalStudentsTab(QWidget):
    add_requested = pyqtSignal()
    record_selection_changed = pyqtSignal(int)
    save_requested = pyqtSignal()
    delete_requested = pyqtSignal()
    revert_requested = pyqtSignal()
    unlock_for_student_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        toolbar = cQToolbar("Alumnos Internos Registrados", self)
        add_action = toolbar.addAction("Agregar Alumno")
        add_action.triggered.connect(lambda _checked=False: self.add_requested.emit())

        delivery_row = QHBoxLayout()
        self.delivery_label = QLabel("Equipo a entregar:", self)
        self.equipment_combo = QComboBox(self)
        self.equipment_combo.setMinimumWidth(230)
        self.unlock_for_student_button = QPushButton(
            "Desbloquear para este usuario", self
        )
        self.unlock_for_student_button.setEnabled(False)
        self.equipment_combo.currentIndexChanged.connect(
            self._update_unlock_button_state
        )
        self.unlock_for_student_button.clicked.connect(
            lambda _checked=False: self.unlock_for_student_requested.emit()
        )
        delivery_row.addWidget(self.delivery_label)
        delivery_row.addWidget(self.equipment_combo, 1)
        delivery_row.addWidget(self.unlock_for_student_button)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.table = cQTableW(0, 6, splitter)
        self.table.setHorizontalHeaderLabels(["Índice", "Nombres", "Apellidos", "Email", "Facultad", "Expediente"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

        self.editor_panel = RegisteredUserEditor("student", splitter)
        self.editor_panel.save_requested.connect(self.save_requested.emit)
        self.editor_panel.delete_requested.connect(self.delete_requested.emit)
        self.editor_panel.revert_requested.connect(self.revert_requested.emit)
        splitter.addWidget(self.table)
        splitter.addWidget(self.editor_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([660, 390])
        layout.addWidget(toolbar)
        layout.addLayout(delivery_row)
        layout.addWidget(splitter)

    def set_equipment_options(self, kiosks):
        selected_host = self.equipment_combo.currentData()
        self.equipment_combo.blockSignals(True)
        self.equipment_combo.clear()
        if not kiosks:
            self.equipment_combo.addItem("No hay equipos registrados", None)
            self.equipment_combo.setEnabled(False)
        else:
            self.equipment_combo.setEnabled(True)
            self.equipment_combo.addItem("Selecciona un equipo...", None)
            for kiosk in kiosks:
                self.equipment_combo.addItem(kiosk.name, kiosk.host)
            selected_index = self.equipment_combo.findData(selected_host)
            if selected_index >= 0:
                self.equipment_combo.setCurrentIndex(selected_index)
        self.equipment_combo.blockSignals(False)
        self._update_unlock_button_state()

    def selected_equipment_host(self):
        value = self.equipment_combo.currentData()
        return str(value).strip() if value else ""

    def set_student_selected(self, selected):
        self._student_selected = bool(selected)
        self._update_unlock_button_state()

    def _update_unlock_button_state(self, *_args):
        self.unlock_for_student_button.setEnabled(
            bool(getattr(self, "_student_selected", False))
            and bool(self.equipment_combo.currentData())
        )

    def _on_selection_changed(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.record_selection_changed.emit(-1)
            return
        item = self.table.item(rows[0].row(), 0)
        record_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        self.record_selection_changed.emit(int(record_id) if record_id is not None else -1)

    def set_records(self, records, selected_id=None, emit_selection=True):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        selected_row = None
        for row, record in enumerate(records):
            self.table.insertRow(row)
            item = QTableWidgetItem(str(row + 1))
            item.setData(Qt.ItemDataRole.UserRole, int(record["id"]))
            self.table.setItem(row, 0, item)
            for column, key in enumerate(("nombres", "apellidos", "email", "facultad", "expediente"), start=1):
                self.table.setItem(row, column, QTableWidgetItem(str(record.get(key, "") or "")))
            if selected_id is not None and int(record["id"]) == int(selected_id):
                selected_row = row
        if selected_row is not None:
            self.table.selectRow(selected_row)
        else:
            self.table.clearSelection()
        self.table.blockSignals(False)
        if emit_selection:
            self.record_selection_changed.emit(int(selected_id) if selected_row is not None else -1)
