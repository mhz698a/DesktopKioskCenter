from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QAbstractItemView, QHeaderView, QSplitter, QTableWidgetItem, QVBoxLayout, QWidget

from css.cqtoolbar import cQToolbar
from css.cQTablewidget import cQTableW
from tabs.registered_user_editor import RegisteredUserEditor


class ExternalUsersTab(QWidget):
    add_requested = pyqtSignal()
    record_selection_changed = pyqtSignal(int)
    save_requested = pyqtSignal()
    delete_requested = pyqtSignal()
    revert_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        toolbar = cQToolbar("Usuarios Externos Registrados", self)
        add_action = toolbar.addAction("Agregar Usuario")
        add_action.triggered.connect(lambda _checked=False: self.add_requested.emit())

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.table = cQTableW(0, 5, splitter)
        self.table.setHorizontalHeaderLabels(["Índice", "Nombres", "Apellidos", "Tipo de usuario", "Universidad"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

        self.editor_panel = RegisteredUserEditor("external", splitter)
        self.editor_panel.save_requested.connect(self.save_requested.emit)
        self.editor_panel.delete_requested.connect(self.delete_requested.emit)
        self.editor_panel.revert_requested.connect(self.revert_requested.emit)
        splitter.addWidget(self.table)
        splitter.addWidget(self.editor_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([660, 390])
        layout.addWidget(toolbar)
        layout.addWidget(splitter)

    def _on_selection_changed(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.record_selection_changed.emit(-1)
            return
        item = self.table.item(rows[0].row(), 0)
        record_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        self.record_selection_changed.emit(int(record_id) if record_id is not None else -1)

    def set_records(self, records, selected_id=None):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        selected_row = None
        for row, record in enumerate(records):
            self.table.insertRow(row)
            item = QTableWidgetItem(str(row + 1))
            item.setData(Qt.ItemDataRole.UserRole, int(record["id"]))
            self.table.setItem(row, 0, item)
            for column, key in enumerate(("nombres", "apellidos", "tipo_usuario", "universidad"), start=1):
                self.table.setItem(row, column, QTableWidgetItem(str(record.get(key, "") or "")))
            if selected_id is not None and int(record["id"]) == int(selected_id):
                selected_row = row
        if selected_row is not None:
            self.table.selectRow(selected_row)
        else:
            self.table.clearSelection()
        self.table.blockSignals(False)
        self.record_selection_changed.emit(int(selected_id) if selected_row is not None else -1)
