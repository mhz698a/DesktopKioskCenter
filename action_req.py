import requests
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal


class ActionWorkerSignals(QObject):
    success = pyqtSignal(str, str)
    error = pyqtSignal(str, str)
    finished = pyqtSignal()


class ActionWorker(QRunnable):
    def __init__(self, kiosk, action, base_url, headers):
        super().__init__()
        self.kiosk = kiosk
        self.action = action
        self.base_url = base_url
        self.headers = headers
        self.signals = ActionWorkerSignals()

    def _emit_error(self, title, message):
        try:
            self.signals.error.emit(title, message)
        except RuntimeError:
            return

    def run(self):
        try:
            response = requests.post(
                f"{self.base_url}/api/kiosk/{self.action}",
                headers=self.headers,
                timeout=(2, 2),
            )

            if response.status_code == 202:
                self.signals.success.emit(
                    "Operación aceptada",
                    f"Se aceptó la acción «{self.action}» para «{self.kiosk.name}».",
                )
                return
            if response.status_code == 401:
                self._emit_error(
                    "Error de autenticación",
                    f"No autorizado en «{self.kiosk.name}». Revisa el token de acceso.",
                )
                return
            if response.status_code == 404:
                self._emit_error(
                    "Ruta no encontrada",
                    f"La ruta de {self.action} no existe en «{self.kiosk.name}».",
                )
                return

            self._emit_error(
                "Error en la petición",
                f"HTTP {response.status_code} en «{self.kiosk.name}»:\n{response.text[:200]}",
            )
        except requests.RequestException as exc:
            self._emit_error(
                "Error de comunicación",
                f"No se pudo conectar con «{self.kiosk.name}».\n\n{exc}",
            )
        finally:
            try:
                self.signals.finished.emit()
            except RuntimeError:
                return
