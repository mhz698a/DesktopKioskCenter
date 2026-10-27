from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from utils import format_duration
from css.cqtoolbar import cQToolbar
from css.cQTablewidget import cQTableW

class EquipmentTab(QWidget):
    add_single_requested = pyqtSignal()
    add_multiple_requested = pyqtSignal()
    selection_changed = pyqtSignal(int)
    lock_requested = pyqtSignal()
    unlock_requested = pyqtSignal()
    delete_requested = pyqtSignal()
    send_ip_requested = pyqtSignal()
    save_requested = pyqtSignal()
    revert_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        toolbar = cQToolbar("Equipos", self)
        toolbar.setMovable(False)

        add_action = toolbar.addAction("Agregar Equipo")
        add_action.triggered.connect(lambda _checked=False: self.add_single_requested.emit())
        add_multiple_action = toolbar.addAction("Agregar varios equipos")
        add_multiple_action.triggered.connect(lambda _checked=False: self.add_multiple_requested.emit())

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.table = cQTableW(0, 4, splitter)
        self.table.setHorizontalHeaderLabels(
            ["Nombre del Equipo", "IP del Equipo", "Estado", "Tiempo usando"]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)

        self.editor_panel = QWidget(splitter)
        editor_layout = QVBoxLayout(self.editor_panel)
        editor_form = QFormLayout()

        self.name_input = QLineEdit(self.editor_panel)
        self.host_input = QLineEdit(self.editor_panel)
        self.port_input = QLineEdit("7085", self.editor_panel)
        self.port_input.setReadOnly(True)
        self.state_input = QLineEdit(self.editor_panel)
        self.state_input.setReadOnly(True)

        editor_form.addRow("Nombre del Equipo:", self.name_input)
        editor_form.addRow("IP del Cliente:", self.host_input)
        editor_form.addRow("Puerto (Solo Lectura):", self.port_input)
        editor_form.addRow("Estado (Solo Lectura):", self.state_input)
        editor_layout.addLayout(editor_form)

        action_row = QHBoxLayout()
        self.lock_button = QPushButton("Bloquear", self.editor_panel)
        self.unlock_button = QPushButton("Desbloquear", self.editor_panel)
        self.delete_button = QPushButton("Eliminar", self.editor_panel)
        action_row.addWidget(self.lock_button)
        action_row.addWidget(self.unlock_button)
        action_row.addWidget(self.delete_button)
        editor_layout.addLayout(action_row)

        send_ip_row = QHBoxLayout()
        self.send_ip_button = QPushButton("Enviar IP de este servidor al PC cliente seleccionado", self.editor_panel)
        send_ip_row.addWidget(self.send_ip_button)
        send_ip_row.addStretch(1)
        editor_layout.addLayout(send_ip_row)

        edit_row = QHBoxLayout()
        self.save_button = QPushButton("Guardar cambios", self.editor_panel)
        self.revert_button = QPushButton("Revertir cambios", self.editor_panel)
        edit_row.addWidget(self.save_button)
        edit_row.addWidget(self.revert_button)
        editor_layout.addLayout(edit_row)
        editor_layout.addStretch(1)

        self.lock_button.clicked.connect(lambda _checked=False: self.lock_requested.emit())
        self.unlock_button.clicked.connect(lambda _checked=False: self.unlock_requested.emit())
        self.delete_button.clicked.connect(lambda _checked=False: self.delete_requested.emit())
        self.send_ip_button.clicked.connect(lambda _checked=False: self.send_ip_requested.emit())
        self.save_button.clicked.connect(lambda _checked=False: self.save_requested.emit())
        self.revert_button.clicked.connect(lambda _checked=False: self.revert_requested.emit())

        splitter.addWidget(self.table)
        splitter.addWidget(self.editor_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([680, 380])

        layout.addWidget(toolbar)
        layout.addWidget(splitter)
        self.set_editor_enabled(False)

    def _on_table_selection_changed(self):
        selected_rows = self.table.selectionModel().selectedRows()
        self.selection_changed.emit(selected_rows[0].row() if selected_rows else -1)

    def set_equipment_rows(self, kiosks, selected_index=None):
        self.table.blockSignals(True)
        self.table.setRowCount(0)

        for row, kiosk in enumerate(kiosks):
            self.table.insertRow(row)
            values = (
                kiosk.name,
                f"{kiosk.host}:{kiosk.port}",
                self.state_label(kiosk.state),
                format_duration(kiosk.locked_seconds),
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))

        if selected_index is not None and 0 <= selected_index < len(kiosks):
            self.table.selectRow(selected_index)
        else:
            self.table.clearSelection()

        self.table.blockSignals(False)

    @staticmethod
    def state_label(state):
        return {
            "locked": "Disponible",
            "unlocked": "En uso",
            "offline": "Sin conexión",
            "error": "Error",
        }.get(state, state)

    def set_editor_enabled(self, enabled):
        self.editor_panel.setEnabled(enabled)

    def set_editor_values(self, kiosk):
        self.name_input.setText(kiosk.name)
        self.host_input.setText(kiosk.host)
        self.port_input.setText(str(kiosk.port))
        self.state_input.setText(self.state_label(kiosk.state))

    def clear_editor(self):
        self.name_input.clear()
        self.host_input.clear()
        self.port_input.setText("7085")
        self.state_input.clear()

    def get_editor_values(self):
        return self.name_input.text().strip(), self.host_input.text().strip()

    def update_equipment_status(self, index, kiosk):
        if not 0 <= index < self.table.rowCount():
            return
        values = (
            kiosk.name,
            f"{kiosk.host}:{kiosk.port}",
            self.state_label(kiosk.state),
            format_duration(kiosk.locked_seconds),
        )
        for column, value in enumerate(values):
            item = self.table.item(index, column)
            if item is None:
                item = QTableWidgetItem()
                self.table.setItem(index, column, item)
            item.setText(value)

        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows and selected_rows[0].row() == index:
            self.state_input.setText(self.state_label(kiosk.state))
