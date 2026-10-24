import requests
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from const import Kiosk


class PollWorkerSignals(QObject):
    finished = pyqtSignal(int, str, object)


class PollWorker(QRunnable):
    def __init__(self, index: int, kiosk: Kiosk, base_url: str, headers: dict):
        super().__init__()
        self.index = index
        self.kiosk = kiosk
        self.base_url = base_url
        self.headers = headers
        self.signals = PollWorkerSignals()

    def _emit_finished(self, state: str, seconds):
        try:
            self.signals.finished.emit(self.index, state, seconds)
        except RuntimeError:
            # Qt ya destruyó las señales durante el cierre de la aplicación.
            return

    def run(self):
        try:
            response = requests.get(
                f"{self.base_url}/api/kiosk/status",
                headers=self.headers,
                timeout=(1.5, 1.5),
            )
            response.raise_for_status()
            data = response.json()
            self._emit_finished(data.get("state", "error"), data.get("locked_seconds"))
        except (requests.RequestException, ValueError):
            self._emit_finished("offline", None)
