import requests
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal
from const import Kiosk

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