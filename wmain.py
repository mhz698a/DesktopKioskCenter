import ipaddress
import socket
import platform

import pywinstyles
from PyQt6.QtCore import QDate, QTime, QTimer, QThreadPool, Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QTabWidget, QVBoxLayout, QWidget

from css.apply_qss import apply_css_sheet
from database import Database
from tabs.equipment.backend import EquipmentBackend
from tabs.equipment.build import EquipmentTab
from tabs.external_users.backend import ExternalUsersBackend
from tabs.external_users.build import ExternalUsersTab
from tabs.internal_students.backend import InternalStudentsBackend
from tabs.internal_students.build import InternalStudentsTab
from tabs.received_logins.backend import ReceivedLoginsBackend
from tabs.received_logins.build import ReceivedLoginsTab
from tabs.access_logs.backend import AccessLogsBackend
from tabs.access_logs.build import AccessLogsTab


class MainWindow(QMainWindow):
    def __init__(self, database: Database | None = None):
        super().__init__()
        self.setWindowTitle("DesktopKioskCenter")
        self.resize(1100, 620)
        self._closing = False

        if platform.system() == "Windows":
            pywinstyles.apply_style(self, "dark")

        self.database = database or Database()
        # initialize() es idempotente; garantiza que las tablas existan si la ventana
        # se inicia directamente desde una prueba o desde otro punto de entrada.
        self.database.initialize()

        self.threadpool = QThreadPool(self)
        self.threadpool.setMaxThreadCount(8)

        root = QWidget(self)
        root.setObjectName("RootMain")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(12, 10, 12, 12)
        root_layout.setSpacing(10)

        header = QWidget(root)
        header.setObjectName("applicationHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 10)

        self.application_title = QLabel("DesktopKioskCenter", header)
        self.application_title.setObjectName("applicationTitle")

        right_header = QVBoxLayout()
        right_header.setSpacing(2)
        self.clock_label = QLabel(header)
        self.clock_label.setObjectName("clockLabel")
        self.date_label = QLabel(header)
        self.date_label.setObjectName("dateLabel")
        self.server_ip_label = QLabel("IP del servidor: detectando…", header)
        self.server_ip_label.setObjectName("serverIpLabel")

        for label in (self.clock_label, self.date_label, self.server_ip_label):
            label.setAlignment(Qt.AlignmentFlag.AlignRight)

        right_header.addWidget(self.clock_label)
        right_header.addWidget(self.date_label)
        right_header.addWidget(self.server_ip_label)
        header_layout.addWidget(self.application_title, 1)
        header_layout.addLayout(right_header)

        self.tabs = QTabWidget(root)
        self.equipment_tab = EquipmentTab(self.tabs)
        self.internal_students_tab = InternalStudentsTab(self.tabs)
        self.external_users_tab = ExternalUsersTab(self.tabs)
        self.received_logins_tab = ReceivedLoginsTab(self.tabs)
        self.access_logs_tab = AccessLogsTab(self.tabs)

        self.tabs.setStyleSheet(apply_css_sheet("css/qtabwidget.css"))
        self.tabs.addTab(self.equipment_tab, "Equipos")
        self.tabs.addTab(
            self.internal_students_tab, "Alumnos Internos Registrados"
        )
        self.tabs.addTab(
            self.external_users_tab, "Usuarios Externos Registrados"
        )
        self.tabs.addTab(self.received_logins_tab, "Logs de peticiones")
        self.tabs.addTab(self.access_logs_tab, "Logs de accesos")

        self.equipment_backend = EquipmentBackend(
            self.equipment_tab, self.threadpool, self, database=self.database
        )
        self.internal_students_backend = InternalStudentsBackend(
            self.internal_students_tab, self.database, self
        )
        self.external_users_backend = ExternalUsersBackend(
            self.external_users_tab, self.database, self
        )
        self.received_logins_backend = ReceivedLoginsBackend(
            self.received_logins_tab, self.database, self
        )
        self.access_logs_backend = AccessLogsBackend(
            self.access_logs_tab, self.database, self
        )

        root_layout.addWidget(header)
        root_layout.addWidget(self.tabs, 1)
        self.setCentralWidget(root)
        self.setStyleSheet(apply_css_sheet("css/qmainwin.css"))

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_header_clock)
        self.clock_timer.start(1000)

        self.server_ip_timer = QTimer(self)
        self.server_ip_timer.timeout.connect(self.update_server_ip)
        self.server_ip_timer.start(15000)

        self.update_header_clock()
        self.update_server_ip()

        self.tabs.currentChanged.connect(self.refresh_active_data_tab)
        self.data_refresh_timer = QTimer(self)
        self.data_refresh_timer.timeout.connect(self.refresh_active_data_tab)
        self.data_refresh_timer.start(2000)

    def refresh_active_data_tab(self, _index=None):
        """Actualiza la pestaña visible para reflejar peticiones REST recién recibidas."""
        if self._closing:
            return

        try:
            index = self.tabs.currentIndex()
            if index == 1:
                self.internal_students_backend.refresh(preserve_editor=True)
            elif index == 2:
                self.external_users_backend.refresh(preserve_editor=True)
            elif index == 3:
                self.received_logins_backend.refresh()
            elif index == 4:
                self.access_logs_backend.refresh()
        except Exception:
            # Un fallo transitorio de lectura no debe cerrar la interfaz; el siguiente
            # ciclo vuelve a consultar SQLite y actualizará la tabla si está disponible.
            import logging
            logging.getLogger(__name__).exception(
                "No se pudo actualizar la pestaña de datos desde SQLite."
            )

    def update_header_clock(self):
        self.clock_label.setText(QTime.currentTime().toString("HH:mm:ss"))
        self.date_label.setText(QDate.currentDate().toString("dd/MM/yyyy"))

    @staticmethod
    def detect_server_ip():
        """Detecta la IP local preferida para enrutar tráfico IPv4."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                probe.connect(("192.0.2.1", 80))
                address = probe.getsockname()[0]
                if address and not ipaddress.ip_address(address).is_loopback:
                    return address
        except OSError:
            pass

        candidates = set()
        try:
            for result in socket.getaddrinfo(
                socket.gethostname(), None, socket.AF_INET, socket.SOCK_DGRAM
            ):
                address = result[4][0]
                parsed = ipaddress.ip_address(address)
                if not parsed.is_loopback and not parsed.is_link_local:
                    candidates.add(address)
        except OSError:
            pass

        if not candidates:
            return "No disponible"

        private_candidates = sorted(
            address for address in candidates
            if ipaddress.ip_address(address).is_private
        )
        return (private_candidates or sorted(candidates))[0]

    def update_server_ip(self):
        self.server_ip_label.setText(
            f"IP del servidor: {self.detect_server_ip()}"
        )

    def closeEvent(self, event):
        self._closing = True
        self.clock_timer.stop()
        self.server_ip_timer.stop()
        self.data_refresh_timer.stop()
        self.equipment_backend.stop()
        self.threadpool.clear()
        self.threadpool.waitForDone()
        self.equipment_backend.release_workers()
        event.accept()
