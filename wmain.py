import json
import requests

from PyQt6.QtCore import QTimer, QThreadPool
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from action_req import ActionWorker
from add_pc_dlg import KioskDialog
from const import BASE_DIR, Kiosk
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
    COL_ACTIONS = 4

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DesktopKioskCenter")
        self.resize(1100, 620)

        self.kiosks = load_kiosks()
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

        # Crear el pool para peticiones en segundo plano.
        self.threadpool = QThreadPool.globalInstance()

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

        self.table = QTableWidget(0, 5, self.equipment_tab)
        self.configure_table(
            self.table,
            [
                "Nombre del Equipo",
                "IP del Equipo",
                "Estado",
                "Tiempo usando",
                "Decisión",
            ],
        )

        layout.addWidget(toolbar)
        layout.addWidget(self.table)
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

    def refresh_table(self):
        self.table.setRowCount(0)

        for index, kiosk in enumerate(self.kiosks):
            self.table.insertRow(index)

            self.table.setItem(index, self.COL_NAME, QTableWidgetItem(kiosk.name))
            self.table.setItem(
                index,
                self.COL_IP,
                QTableWidgetItem(f"{kiosk.host}:{kiosk.port}"),
            )
            self.table.setItem(
                index,
                self.COL_STATE,
                QTableWidgetItem(self.state_label(kiosk.state)),
            )
            self.table.setItem(
                index,
                self.COL_TIME,
                QTableWidgetItem(format_duration(kiosk.locked_seconds)),
            )

            self.table.setCellWidget(
                index,
                self.COL_ACTIONS,
                self.make_action_widget(index, kiosk),
            )

        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(self.COL_ACTIONS, 330)

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

    def make_action_widget(self, row: int, kiosk: Kiosk) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 2, 4, 2)

        lock_button = QPushButton("Bloquear")
        unlock_button = QPushButton("Desbloquear")
        edit_button = QPushButton("Editar")
        remove_button = QPushButton("Quitar")

        lock_button.clicked.connect(
            lambda _=False, i=row: self.send_action(i, "lock")
        )
        unlock_button.clicked.connect(
            lambda _=False, i=row: self.send_action(i, "unlock")
        )
        edit_button.clicked.connect(
            lambda _=False, i=row: self.edit_kiosk(i)
        )
        remove_button.clicked.connect(
            lambda _=False, i=row: self.remove_kiosk(i)
        )

        layout.addWidget(lock_button)
        layout.addWidget(unlock_button)
        layout.addWidget(edit_button)
        layout.addWidget(remove_button)

        return container

    def base_url(self, kiosk: Kiosk) -> str:
        return f"http://{kiosk.host}:{kiosk.port}"

    def auth_headers(self, kiosk: Kiosk) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {kiosk.token}",
            "Content-Type": "application/json",
        }

    def send_action(self, index: int, action: str):
        kiosk = self.kiosks[index]
        worker = ActionWorker(
            kiosk,
            action,
            self.base_url(kiosk),
            self.auth_headers(kiosk),
        )

        worker.signals.error.connect(self.show_action_error)
        self.threadpool.start(worker)

    def show_action_error(self, title: str, message: str):
        QMessageBox.critical(self, title, message)

    def poll_status(self):
        for index, kiosk in enumerate(self.kiosks):
            worker = PollWorker(
                index,
                kiosk,
                self.base_url(kiosk),
                self.auth_headers(kiosk),
            )
            worker.signals.finished.connect(self.on_poll_finished)
            self.threadpool.start(worker)

    def on_poll_finished(self, index: int, new_state: str, new_seconds: object):
        if index >= len(self.kiosks):
            return

        kiosk = self.kiosks[index]
        changed = (
            kiosk.state != new_state or kiosk.locked_seconds != new_seconds
        )

        if changed:
            kiosk.state = new_state
            kiosk.locked_seconds = new_seconds
            self.update_row(index)

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

        self.kiosks.append(dialog.get_kiosk())
        save_kiosks(self.kiosks)
        self.refresh_table()

    def edit_kiosk(self, index: int):
        kiosk = self.kiosks[index]
        dialog = KioskDialog(self, kiosk)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        updated = dialog.get_kiosk()
        updated.state = kiosk.state
        updated.locked_seconds = kiosk.locked_seconds

        self.kiosks[index] = updated
        save_kiosks(self.kiosks)
        self.refresh_table()

    def remove_kiosk(self, index: int):
        kiosk = self.kiosks[index]

        answer = QMessageBox.question(
            self,
            "Quitar equipo",
            f"¿Quitar «{kiosk.name}» de la lista?",
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        self.kiosks.pop(index)
        save_kiosks(self.kiosks)
        self.refresh_table()

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

    def show_about(self):
        QMessageBox.information(
            self,
            "Acerca de DesktopKioskCenter",
            "DesktopKioskCenter MVP\n"
            "Gestión centralizada de clientes Kiosk mediante HTTP + Bearer Token.",
        )
