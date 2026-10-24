import json
import requests

from PyQt6.QtCore import QTimer, QThreadPool, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from action_req import ActionWorker
from add_pc_dlg import KioskDialog
from const import BASE_DIR, DEFAULT_TOKEN, Kiosk
from pollstatus import PollWorker
from user_record_dialog import UserRecordDialog
from utils import load_kiosks, format_duration, save_kiosks


INTERNAL_STUDENTS_FILE = BASE_DIR / "internal_students.json"
EXTERNAL_USERS_FILE = BASE_DIR / "external_users.json"

INTERNAL_STUDENT_FIELDS = [
    ("nombres", "Nombres"),
    ("apellidos", "Apellidos"),
    ("facultad", "Facultad"),
    ("expediente", "Expediente"),
]

EXTERNAL_USER_FIELDS = [
    ("nombres", "Nombres"),
    ("apellidos", "Apellidos"),
    ("tipo_usuario", "Tipo de usuario"),
    ("universidad", "Universidad Perteneciente"),
]


def load_records(path, fields):
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []

    if not isinstance(data, list):
        return []

    records = []
    for item in data:
        if isinstance(item, dict):
            records.append({
                key: str(item.get(key, "") or "")
                for key, _label in fields
            })
    return records


def save_records(path, records):
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(records, indent=2, ensure_ascii=False)
    temporary_path.write_text(payload, encoding="utf-8")
    temporary_path.replace(path)


class MainWindow(QMainWindow):
    COL_NAME = 0
    COL_IP = 1
    COL_STATE = 2
    COL_TIME = 3

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DesktopKioskCenter")
        self.resize(1100, 620)

        self._closing = False
        self.selected_kiosk_index = None
        self.kiosks = load_kiosks()
        token_changed = False
        for kiosk in self.kiosks:
            if kiosk.token != DEFAULT_TOKEN:
                kiosk.token = DEFAULT_TOKEN
                token_changed = True
        if token_changed:
            try:
                save_kiosks(self.kiosks)
            except OSError:
                # El token fijo se usa aunque no sea posible actualizar el archivo.
                pass

        self.internal_students = load_records(
            INTERNAL_STUDENTS_FILE, INTERNAL_STUDENT_FIELDS
        )
        self.external_users = load_records(
            EXTERNAL_USERS_FILE, EXTERNAL_USER_FIELDS
        )

        self.tabs = QTabWidget(self)
        self.build_equipment_tab()
        self.build_internal_students_tab()
        self.build_external_users_tab()
        self.setCentralWidget(self.tabs)

        self.build_menus()
        self.refresh_table()
        self.refresh_internal_students_table()
        self.refresh_external_users_table()

        # Pool propio para esperar a los trabajadores al cerrar esta ventana.
        self.threadpool = QThreadPool(self)
        self.threadpool.setMaxThreadCount(8)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_status)
        self.timer.start(3000)

        self.poll_status()

    @staticmethod
    def configure_table(table, headers):
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)

    def build_equipment_tab(self):
        self.equipment_tab = QWidget(self.tabs)
        layout = QVBoxLayout(self.equipment_tab)

        toolbar = QToolBar("Equipos", self.equipment_tab)
        toolbar.setMovable(False)
        add_equipment_action = toolbar.addAction("Agregar Equipo")
        add_equipment_action.triggered.connect(self.add_kiosk)

        splitter = QSplitter(Qt.Orientation.Horizontal, self.equipment_tab)
        self.table = QTableWidget(0, 4, splitter)
        self.configure_table(
            self.table,
            ["Nombre del Equipo", "IP del Equipo", "Estado", "Tiempo usando"],
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self.on_equipment_selection_changed)

        self.editor_panel = QWidget(splitter)
        editor_layout = QVBoxLayout(self.editor_panel)
        editor_form = QFormLayout()
        self.edit_name = QLineEdit(self.editor_panel)
        self.edit_host = QLineEdit(self.editor_panel)
        self.edit_port = QLineEdit(self.editor_panel)
        self.edit_state = QLineEdit(self.editor_panel)
        self.edit_state.setReadOnly(True)
        editor_form.addRow("Nombre:", self.edit_name)
        editor_form.addRow("IP / Host:", self.edit_host)
        editor_form.addRow("Puerto:", self.edit_port)
        editor_form.addRow("Estado:", self.edit_state)
        editor_layout.addLayout(editor_form)

        action_buttons = QHBoxLayout()
        self.lock_button = QPushButton("Bloquear", self.editor_panel)
        self.unlock_button = QPushButton("Desbloquear", self.editor_panel)
        self.delete_button = QPushButton("Eliminar", self.editor_panel)
        action_buttons.addWidget(self.lock_button)
        action_buttons.addWidget(self.unlock_button)
        action_buttons.addWidget(self.delete_button)
        editor_layout.addLayout(action_buttons)

        edit_buttons = QHBoxLayout()
        self.save_button = QPushButton("Guardar cambios", self.editor_panel)
        self.revert_button = QPushButton("Revertir cambios", self.editor_panel)
        edit_buttons.addWidget(self.save_button)
        edit_buttons.addWidget(self.revert_button)
        editor_layout.addLayout(edit_buttons)
        editor_layout.addStretch(1)

        self.lock_button.clicked.connect(lambda _=False: self.send_selected_action("lock"))
        self.unlock_button.clicked.connect(lambda _=False: self.send_selected_action("unlock"))
        self.delete_button.clicked.connect(self.remove_selected_kiosk)
        self.save_button.clicked.connect(self.save_kiosk_changes)
        self.revert_button.clicked.connect(self.revert_kiosk_changes)

        splitter.addWidget(self.table)
        splitter.addWidget(self.editor_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([680, 380])
        self.editor_panel.setEnabled(False)

        layout.addWidget(toolbar)
        layout.addWidget(splitter)
        self.tabs.addTab(self.equipment_tab, "Equipos")

    def build_internal_students_tab(self):
        self.internal_students_tab = QWidget(self.tabs)
        layout = QVBoxLayout(self.internal_students_tab)

        toolbar = QToolBar("Alumnos Internos Registrados", self.internal_students_tab)
        toolbar.setMovable(False)
        add_student_action = toolbar.addAction("Agregar Alumno")
        add_student_action.triggered.connect(self.add_internal_student)

        self.internal_students_table = QTableWidget(0, 5, self.internal_students_tab)
        self.configure_table(
            self.internal_students_table,
            ["Indice", "Nombres", "Apellidos", "Facultad", "Expediente"],
        )

        layout.addWidget(toolbar)
        layout.addWidget(self.internal_students_table)
        self.tabs.addTab(
            self.internal_students_tab, "Alumnos Internos Registrados"
        )

    def build_external_users_tab(self):
        self.external_users_tab = QWidget(self.tabs)
        layout = QVBoxLayout(self.external_users_tab)

        toolbar = QToolBar("Usuarios Externos Registrados", self.external_users_tab)
        toolbar.setMovable(False)
        add_user_action = toolbar.addAction("Agregar Usuario")
        add_user_action.triggered.connect(self.add_external_user)

        self.external_users_table = QTableWidget(0, 5, self.external_users_tab)
        self.configure_table(
            self.external_users_table,
            [
                "Indice",
                "Nombres",
                "Apellidos",
                "Tipo de usuario",
                "Universidad Perteneciente",
            ],
        )

        layout.addWidget(toolbar)
        layout.addWidget(self.external_users_table)
        self.tabs.addTab(
            self.external_users_tab, "Usuarios Externos Registrados"
        )

    def build_menus(self):
        menu_archivo = self.menuBar().addMenu("Archivo")
        action_exit = menu_archivo.addAction("Salir")
        action_exit.triggered.connect(self.close)

        menu_ayuda = self.menuBar().addMenu("Ayuda")
        action_about = menu_ayuda.addAction("Acerca de...")
        action_about.triggered.connect(self.show_about)

    def refresh_table(self, select_index=None):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for index, kiosk in enumerate(self.kiosks):
            self.table.insertRow(index)
            self.table.setItem(index, self.COL_NAME, QTableWidgetItem(kiosk.name))
            self.table.setItem(index, self.COL_IP, QTableWidgetItem(f"{kiosk.host}:{kiosk.port}"))
            self.table.setItem(index, self.COL_STATE, QTableWidgetItem(self.state_label(kiosk.state)))
            self.table.setItem(index, self.COL_TIME, QTableWidgetItem(format_duration(kiosk.locked_seconds)))
        self.table.resizeColumnsToContents()
        if select_index is not None and 0 <= select_index < len(self.kiosks):
            self.table.selectRow(select_index)
        else:
            self.table.clearSelection()
        self.table.blockSignals(False)
        self.on_equipment_selection_changed()

    def on_equipment_selection_changed(self):
        if self._closing:
            return
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            self.selected_kiosk_index = None
            self.editor_panel.setEnabled(False)
            self.edit_name.clear()
            self.edit_host.clear()
            self.edit_port.clear()
            self.edit_state.clear()
            return
        index = selected_rows[0].row()
        if not 0 <= index < len(self.kiosks):
            self.selected_kiosk_index = None
            self.editor_panel.setEnabled(False)
            return
        self.selected_kiosk_index = index
        self.editor_panel.setEnabled(True)
        self.revert_kiosk_changes()

    @staticmethod
    def refresh_records_table(table, records, fields):
        table.setRowCount(0)

        for row_index, record in enumerate(records, start=1):
            table.insertRow(row_index - 1)
            table.setItem(
                row_index - 1, 0, QTableWidgetItem(str(row_index))
            )

            for column_index, (key, _label) in enumerate(fields, start=1):
                table.setItem(
                    row_index - 1,
                    column_index,
                    QTableWidgetItem(record.get(key, "")),
                )

        table.resizeColumnsToContents()

    def refresh_internal_students_table(self):
        self.refresh_records_table(
            self.internal_students_table,
            self.internal_students,
            INTERNAL_STUDENT_FIELDS,
        )

    def refresh_external_users_table(self):
        self.refresh_records_table(
            self.external_users_table,
            self.external_users,
            EXTERNAL_USER_FIELDS,
        )

    @staticmethod
    def state_label(state: str) -> str:
        return {
            "locked": "Bloqueado",
            "unlocked": "Desbloqueado",
            "offline": "Sin conexión",
            "error": "Error",
        }.get(state, state)

    def base_url(self, kiosk: Kiosk) -> str:
        return f"http://{kiosk.host}:{kiosk.port}"

    def auth_headers(self, kiosk: Kiosk) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {DEFAULT_TOKEN}",
            "Content-Type": "application/json",
        }

    def send_selected_action(self, action: str):
        index = self.selected_kiosk_index
        if self._closing or index is None or not 0 <= index < len(self.kiosks):
            return
        kiosk = self.kiosks[index]
        worker = ActionWorker(
            kiosk, action, self.base_url(kiosk), self.auth_headers(kiosk)
        )
        worker.signals.error.connect(self.show_action_error)
        self.threadpool.start(worker)

    def show_action_error(self, title: str, message: str):
        if not self._closing:
            QMessageBox.critical(self, title, message)

    def poll_status(self):
        if self._closing:
            return
        for index, kiosk in enumerate(self.kiosks):
            worker = PollWorker(
                index, kiosk, self.base_url(kiosk), self.auth_headers(kiosk)
            )
            worker.signals.finished.connect(self.on_poll_finished)
            self.threadpool.start(worker)

    def on_poll_finished(self, index: int, new_state: str, new_seconds: object):
        if self._closing or index >= len(self.kiosks):
            return

        kiosk = self.kiosks[index]
        changed = (
            kiosk.state != new_state or kiosk.locked_seconds != new_seconds
        )

        if changed:
            kiosk.state = new_state
            kiosk.locked_seconds = new_seconds
            self.update_row(index)
            if self.selected_kiosk_index == index:
                self.edit_state.setText(self.state_label(kiosk.state))

    def update_row(self, index: int):
        kiosk = self.kiosks[index]

        state_item = self.table.item(index, self.COL_STATE)
        if state_item:
            state_item.setText(self.state_label(kiosk.state))

        time_item = self.table.item(index, self.COL_TIME)
        if time_item:
            time_item.setText(format_duration(kiosk.locked_seconds))

    def poll_one(self, index: int) -> bool:
        kiosk = self.kiosks[index]

        try:
            response = requests.get(
                f"{self.base_url(kiosk)}/api/kiosk/status",
                headers=self.auth_headers(kiosk),
                timeout=2,
            )
            response.raise_for_status()
            data = response.json()

            new_state = data.get("state", "error")
            new_seconds = data.get("locked_seconds")
            changed = (
                kiosk.state != new_state
                or kiosk.locked_seconds != new_seconds
            )

            kiosk.state = new_state
            kiosk.locked_seconds = new_seconds
            return changed

        except (requests.RequestException, ValueError):
            changed = (
                kiosk.state != "offline" or kiosk.locked_seconds is not None
            )
            kiosk.state = "offline"
            kiosk.locked_seconds = None
            return changed

    def add_kiosk(self):
        dialog = KioskDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        kiosk = dialog.get_kiosk()
        self.kiosks.append(kiosk)
        try:
            save_kiosks(self.kiosks)
        except OSError as exc:
            self.kiosks.pop()
            QMessageBox.critical(self, "Error al guardar", f"No se pudo guardar el equipo.\n\n{exc}")
            return
        self.refresh_table(select_index=len(self.kiosks) - 1)

    def revert_kiosk_changes(self):
        index = self.selected_kiosk_index
        if index is None or not 0 <= index < len(self.kiosks):
            return
        kiosk = self.kiosks[index]
        self.edit_name.setText(kiosk.name)
        self.edit_host.setText(kiosk.host)
        self.edit_port.setText(str(kiosk.port))
        self.edit_state.setText(self.state_label(kiosk.state))

    def save_kiosk_changes(self):
        index = self.selected_kiosk_index
        if index is None or not 0 <= index < len(self.kiosks):
            return
        name = self.edit_name.text().strip()
        host = self.edit_host.text().strip()
        port_text = self.edit_port.text().strip()
        if not name:
            QMessageBox.warning(self, "Validación", "El nombre es obligatorio.")
            self.edit_name.setFocus()
            return
        if not host:
            QMessageBox.warning(self, "Validación", "La IP o host es obligatorio.")
            self.edit_host.setFocus()
            return
        try:
            port = int(port_text)
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Validación", "El puerto debe ser un entero entre 1 y 65535.")
            self.edit_port.setFocus()
            return

        original = self.kiosks[index]
        self.kiosks[index] = Kiosk(
            name=name, host=host, port=port, token=DEFAULT_TOKEN,
            state=original.state, locked_seconds=original.locked_seconds,
        )
        try:
            save_kiosks(self.kiosks)
        except OSError as exc:
            self.kiosks[index] = original
            QMessageBox.critical(self, "Error al guardar", f"No se pudieron guardar los cambios.\n\n{exc}")
            return
        self.refresh_table(select_index=index)

    def remove_selected_kiosk(self):
        index = self.selected_kiosk_index
        if index is None or not 0 <= index < len(self.kiosks):
            return
        kiosk = self.kiosks[index]
        answer = QMessageBox.question(
            self,
            "Eliminar equipo",
            f"¿Eliminar «{kiosk.name}» de la lista?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        removed = self.kiosks.pop(index)
        try:
            save_kiosks(self.kiosks)
        except OSError as exc:
            self.kiosks.insert(index, removed)
            QMessageBox.critical(self, "Error al guardar", f"No se pudo eliminar el equipo.\n\n{exc}")
            return
        next_index = min(index, len(self.kiosks) - 1) if self.kiosks else None
        self.refresh_table(select_index=next_index)

    def add_internal_student(self):
        dialog = UserRecordDialog(
            "Agregar Alumno",
            INTERNAL_STUDENT_FIELDS,
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        record = dialog.get_record()
        updated_records = self.internal_students + [record]
        try:
            save_records(INTERNAL_STUDENTS_FILE, updated_records)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Error al guardar",
                f"No se pudo guardar el alumno.\n\n{exc}",
            )
            return

        self.internal_students = updated_records
        self.refresh_internal_students_table()

    def add_external_user(self):
        dialog = UserRecordDialog(
            "Agregar Usuario",
            EXTERNAL_USER_FIELDS,
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        record = dialog.get_record()
        updated_records = self.external_users + [record]
        try:
            save_records(EXTERNAL_USERS_FILE, updated_records)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Error al guardar",
                f"No se pudo guardar el usuario externo.\n\n{exc}",
            )
            return

        self.external_users = updated_records
        self.refresh_external_users_table()

    def closeEvent(self, event):
        self._closing = True
        if hasattr(self, "timer"):
            self.timer.stop()
        if hasattr(self, "threadpool"):
            self.threadpool.clear()
            self.threadpool.waitForDone()
        event.accept()

    def show_about(self):
        QMessageBox.information(
            self,
            "Acerca de DesktopKioskCenter",
            "DesktopKioskCenter MVP\n"
            "Gestión centralizada de clientes Kiosk mediante HTTP + Bearer Token.",
        )
