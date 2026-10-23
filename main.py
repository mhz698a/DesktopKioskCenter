import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import requests
from PyQt6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)
from PyQt6.QtCore import QTimer, QObject, QRunnable, QThreadPool, pyqtSignal

if getattr(sys, 'frozen', False):
    # Si está ejecutándose como un ejecutable compilado (.exe)
    BASE_DIR = Path(sys.executable).parent
else:
    # Si está ejecutándose directamente como script .py
    BASE_DIR = Path(__file__).parent

DATA_FILE = BASE_DIR / "kiosks.json"

DEFAULT_TOKEN = os.getenv("DESKTOPKIOSK_API_TOKEN", "MiTokenSecreto123")

@dataclass
class Kiosk:
    name: str
    host: str
    port: int = 7085
    token: str = ""
    state: str = "offline"
    locked_seconds: int | None = None

class PollWorkerSignals(QObject):
    # Transmite: (índice_kiosk, estado_nuevo, locked_seconds_nuevo)
    finished = pyqtSignal(int, str, object)
    
class PollWorker(QRunnable):
    def __init__(self, index: int, kiosk: Kiosk, base_url: str, headers: dict):
        super().__init__()
        self.index = index
        self.kiosk = kiosk
        self.base_url = base_url
        self.headers = headers
        self.signals = PollWorkerSignals()

    def run(self):
        try:
            response = requests.get(
                f"{self.base_url}/api/kiosk/status",
                headers=self.headers,
                timeout=2,
            )
            response.raise_for_status()
            data = response.json()
            new_state = data.get("state", "error")
            new_seconds = data.get("locked_seconds")
            self.signals.finished.emit(self.index, new_state, new_seconds)
        except (requests.RequestException, ValueError):
            self.signals.finished.emit(self.index, "offline", None)


def load_kiosks() -> list[Kiosk]:
    if not DATA_FILE.exists():
        return []

    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        return [Kiosk(**item) for item in data]
    except (OSError, ValueError, TypeError):
        return []


def save_kiosks(kiosks: list[Kiosk]) -> None:
    payload = [asdict(kiosk) for kiosk in kiosks]
    DATA_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "—"

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class ActionWorkerSignals(QObject):
    success = pyqtSignal(str, str)  # (titulo, mensaje)
    error = pyqtSignal(str, str)    # (titulo, mensaje)

class ActionWorker(QRunnable):
    def __init__(self, kiosk: Kiosk, action: str, base_url: str, headers: dict):
        super().__init__()
        self.kiosk = kiosk
        self.action = action
        self.base_url = base_url
        self.headers = headers
        self.signals = ActionWorkerSignals()

    def run(self):
        try:
            response = requests.post(
                f"{self.base_url}/api/kiosk/{self.action}",
                headers=self.headers,
                timeout=5,
            )

            if response.status_code == 202:
                # Opcional: Notificar éxito si lo deseas
                return

            if response.status_code == 401:
                self.signals.error.emit(
                    "Error de autenticación",
                    f"No autorizado en «{self.kiosk.name}». Revisa el token de acceso."
                )
                return

            if response.status_code == 404:
                self.signals.error.emit(
                    "Ruta no encontrada",
                    f"La ruta de {self.action} no existe en «{self.kiosk.name}»."
                )
                return

            # Para cualquier otro código de error HTTP
            self.signals.error.emit(
                "Error en la petición",
                f"HTTP {response.status_code} en «{self.kiosk.name}»:\n{response.text[:200]}"
            )

        except requests.RequestException as exc:
            self.signals.error.emit(
                "Error de comunicación",
                f"No se pudo conectar con «{self.kiosk.name}».\n\n{exc}"
            )
            

class KioskDialog(QDialog):
    def __init__(self, parent=None, kiosk: Kiosk | None = None):
        super().__init__(parent)
        self.setWindowTitle("Editar equipo" if kiosk else "Agregar equipo")

        self.name = QLineEdit()
        self.host = QLineEdit()
        self.port = QLineEdit("7085")
        self.token = QLineEdit()

        if kiosk:
            self.name.setText(kiosk.name)
            self.host.setText(kiosk.host)
            self.port.setText(str(kiosk.port))
            self.token.setText(kiosk.token)

        form = QFormLayout()
        form.addRow("Nombre:", self.name)
        form.addRow("IP / Host:", self.host)
        form.addRow("Puerto:", self.port)
        form.addRow("Token:", self.token)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def get_kiosk(self) -> Kiosk:
        return Kiosk(
            name=self.name.text().strip(),
            host=self.host.text().strip(),
            port=int(self.port.text().strip() or "7085"),
            token=self.token.text().strip(),
        )

    def accept(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "Validación", "El nombre es obligatorio.")
            return

        if not self.host.text().strip():
            QMessageBox.warning(self, "Validación", "La IP o host es obligatorio.")
            return

        try:
            port = int(self.port.text().strip())
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Validación", "El puerto debe ser un entero entre 1 y 65535.")
            return

        if not self.token.text().strip():
            self.token.setText(DEFAULT_TOKEN)

        super().accept()


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

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            [
                "Nombre del Equipo",
                "IP del Equipo",
                "Estado",
                "Tiempo usando",
                "Decisión",
            ]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.table.horizontalHeader().setStretchLastSection(True)

        self.setCentralWidget(self.table)

        self.build_menus()
        self.refresh_table()

        # Crear el pool para peticiones en segundo plano
        self.threadpool = QThreadPool.globalInstance()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_status)
        self.timer.start(3000)

        self.poll_status()

    def build_menus(self):
        menu_archivo = self.menuBar().addMenu("Archivo")
        action_exit = menu_archivo.addAction("Salir")
        action_exit.triggered.connect(self.close)

        menu_edicion = self.menuBar().addMenu("Edición")
        action_add = menu_edicion.addAction("Agregar Equipo")
        action_add.triggered.connect(self.add_kiosk)

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
            self.auth_headers(kiosk)
        )
        
        # Conectamos las señales a métodos de la interfaz
        worker.signals.error.connect(self.show_action_error)
        
        # Iniciamos el trabajador en el hilo en segundo plano
        self.threadpool.start(worker)

    def show_action_error(self, title: str, message: str):
        # Este método se ejecuta de forma segura dentro del hilo principal de la UI
        QMessageBox.critical(self, title, message)

    def poll_status(self):
        # Lanza las peticiones en paralelo sin bloquear la UI
        for index, kiosk in enumerate(self.kiosks):
            worker = PollWorker(
                index, 
                kiosk, 
                self.base_url(kiosk), 
                self.auth_headers(kiosk)
            )
            worker.signals.finished.connect(self.on_poll_finished)
            self.threadpool.start(worker)
    
    def on_poll_finished(self, index: int, new_state: str, new_seconds: object):
        if index >= len(self.kiosks):
            return

        kiosk = self.kiosks[index]
        changed = (kiosk.state != new_state or kiosk.locked_seconds != new_seconds)

        if changed:
            kiosk.state = new_state
            kiosk.locked_seconds = new_seconds
            # Actualizamos únicamente la celda/fila afectada sin reconstruir toda la tabla
            self.update_row(index)
            
    def update_row(self, index: int):
        kiosk = self.kiosks[index]
        
        # Actualizar texto de Estado
        state_item = self.table.item(index, self.COL_STATE)
        if state_item:
            state_item.setText(self.state_label(kiosk.state))

        # Actualizar texto de Tiempo
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
            changed = kiosk.state != "offline" or kiosk.locked_seconds is not None
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

    def show_about(self):
        QMessageBox.information(
            self,
            "Acerca de DesktopKioskCenter",
            "DesktopKioskCenter MVP\n"
            "Gestión centralizada de clientes Kiosk mediante HTTP + Bearer Token.",
        )


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
