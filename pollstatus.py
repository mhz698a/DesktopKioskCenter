import requests
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal
from const import Kiosk

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

