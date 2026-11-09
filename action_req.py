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


class ReceiveIPWorker(QRunnable):
    """Envía la IP del servidor a un equipo Kiosk en segundo plano."""

    def __init__(self, kiosk, base_url, headers, server_ip):
        super().__init__()
        self.kiosk = kiosk
        self.base_url = base_url
        self.headers = headers
        self.server_ip = server_ip
        self.signals = ActionWorkerSignals()

    def _emit_error(self, title, message):
        try:
            self.signals.error.emit(title, message)
        except RuntimeError:
            return

    def _emit_success(self, title, message):
        try:
            self.signals.success.emit(title, message)
        except RuntimeError:
            return

    def run(self):
        try:
            response = requests.post(
                f"{self.base_url}/api/kiosk/receive",
                headers=self.headers,
                json={
                    "action": "receive",
                    "data": {"server_control_ip": self.server_ip},
                },
                timeout=(2, 2),
            )

            if not 200 <= response.status_code < 300:
                if response.status_code in (401, 403):
                    self._emit_error(
                        "Error de autenticación",
                        f"El equipo «{self.kiosk.name}» rechazó la petición. Revisa el token de acceso.",
                    )
                elif response.status_code == 404:
                    self._emit_error(
                        "Ruta no encontrada",
                        f"El equipo «{self.kiosk.name}» no tiene disponible la ruta /api/kiosk/receive.",
                    )
                else:
                    self._emit_error(
                        "Error al enviar la IP",
                        f"HTTP {response.status_code} en «{self.kiosk.name}»:\n{response.text[:200]}",
                    )
                return

            self._emit_success(
                "IP enviada",
                f"Se envió la IP del servidor ({self.server_ip}) al equipo «{self.kiosk.name}».",
            )
        except requests.RequestException as exc:
            self._emit_error(
                "Error de comunicación",
                f"No se pudo enviar la IP al equipo «{self.kiosk.name}».\n\n{exc}",
            )
        finally:
            try:
                self.signals.finished.emit()
            except RuntimeError:
                return



class BulkReceiveIPWorker(QRunnable):
    """Envía la IP del servidor a todos los equipos con concurrencia limitada."""

    def __init__(self, kiosks, headers, server_ip, max_workers=8):
        super().__init__()
        self.kiosks = list(kiosks)
        self.headers = dict(headers)
        self.server_ip = str(server_ip)
        self.max_workers = max(1, int(max_workers))
        self.signals = ActionWorkerSignals()

    def _send_one(self, kiosk):
        try:
            response = requests.post(
                f"http://{kiosk.host}:{kiosk.port}/api/kiosk/receive",
                headers=self.headers,
                json={"action": "receive", "data": {"server_control_ip": self.server_ip}},
                timeout=(2, 2),
            )
            if 200 <= response.status_code < 300:
                return kiosk.name, None
            return kiosk.name, (
                f"{kiosk.name}: HTTP {response.status_code} ({response.text[:120]})"
            )
        except requests.RequestException as exc:
            return kiosk.name, f"{kiosk.name}: {exc}"

    def run(self):
        import concurrent.futures

        successes, errors = 0, []
        try:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.max_workers
            ) as executor:
                futures = [executor.submit(self._send_one, kiosk) for kiosk in self.kiosks]
                for future in concurrent.futures.as_completed(futures):
                    try:
                        _name, error = future.result()
                        if error:
                            errors.append(error)
                        else:
                            successes += 1
                    except Exception as exc:
                        errors.append(str(exc))

            summary = (
                f"Envío de IP terminado: {successes} equipo(s) aceptaron la solicitud "
                f"y {len(errors)} fallaron, de {len(self.kiosks)} equipo(s)."
            )
            if errors:
                details = "\n".join(errors[:8])
                if len(errors) > 8:
                    details += f"\n... y {len(errors) - 8} error(es) más."
                self.signals.error.emit("Resultado del envío de IP", summary + "\n\n" + details)
            else:
                self.signals.success.emit("IP enviada", summary)
        finally:
            try:
                self.signals.finished.emit()
            except RuntimeError:
                return


class AssignedSessionWorkerSignals(QObject):
    success = pyqtSignal(object, object, str, str)
    error = pyqtSignal(str, str)
    finished = pyqtSignal(object)


class AssignedSessionWorker(QRunnable):
    """Inicia una sesión remota para la identidad elegida en DesktopKioskCenter."""

    def __init__(self, kiosk, user_data, base_url, headers):
        super().__init__()
        self.kiosk = kiosk
        self.user_data = dict(user_data)
        self.base_url = base_url
        self.headers = dict(headers)
        self.signals = AssignedSessionWorkerSignals()

    def run(self):
        try:
            response = requests.post(
                f"{self.base_url}/api/kiosk/assigned-session",
                headers=self.headers,
                json={
                    "action": "assign_session",
                    "data": self.user_data,
                },
                timeout=(2, 4),
            )
            if response.status_code == 202:
                self.signals.success.emit(
                    self.kiosk,
                    self.user_data,
                    "Sesión iniciada",
                    f"El equipo «{self.kiosk.name}» inició sesión a nombre de "
                    f"«{self.user_data.get('display_name', '')}».",
                )
            elif response.status_code == 401:
                self.signals.error.emit(
                    "Error de autenticación",
                    f"El equipo «{self.kiosk.name}» rechazó la solicitud. Revisa el token.",
                )
            elif response.status_code == 400:
                self.signals.error.emit(
                    "Datos inválidos",
                    f"El equipo «{self.kiosk.name}» rechazó los datos de asignación: "
                    f"{response.text[:200]}",
                )
            elif response.status_code == 404:
                self.signals.error.emit(
                    "Ruta no encontrada",
                    f"El equipo «{self.kiosk.name}» todavía no ofrece "
                    "la ruta /api/kiosk/assigned-session.",
                )
            else:
                self.signals.error.emit(
                    "Error en la petición",
                    f"HTTP {response.status_code} en «{self.kiosk.name}»:\n"
                    f"{response.text[:200]}",
                )
        except requests.RequestException as exc:
            self.signals.error.emit(
                "Error de comunicación",
                f"No se pudo iniciar la sesión en «{self.kiosk.name}».\n\n{exc}",
            )
        finally:
            self.signals.finished.emit(self)


class PCControlWorker(QRunnable):
    """Envía una solicitud autenticada para apagar o reiniciar Windows."""

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
                f"{self.base_url}/api/kiosk/pc-control",
                headers=self.headers,
                json={"action": self.action},
                timeout=(2, 3),
            )

            if response.status_code == 202:
                self.signals.success.emit(
                    "Operación aceptada",
                    f"Se envió la acción «{self.action}» al equipo «{self.kiosk.name}».",
                )
            elif response.status_code == 401:
                self._emit_error(
                    "Error de autenticación",
                    f"No autorizado en «{self.kiosk.name}». Revisa el token de acceso.",
                )
            else:
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


class BulkPCControlWorker(QRunnable):
    """Envía una acción de energía a varios equipos y devuelve un resumen."""

    def __init__(self, kiosks, action, headers, max_workers=8):
        super().__init__()
        self.kiosks = list(kiosks)
        self.action = action
        self.headers = dict(headers)
        self.max_workers = max(1, int(max_workers))
        self.signals = ActionWorkerSignals()

    def _send_one(self, kiosk):
        try:
            response = requests.post(
                f"http://{kiosk.host}:{kiosk.port}/api/kiosk/pc-control",
                headers=self.headers,
                json={"action": self.action},
                timeout=(2, 3),
            )
            if response.status_code == 202:
                return kiosk.name, None
            return kiosk.name, (
                f"{kiosk.name}: HTTP {response.status_code} "
                f"({response.text[:120]})"
            )
        except requests.RequestException as exc:
            return kiosk.name, f"{kiosk.name}: {exc}"

    def run(self):
        import concurrent.futures

        label = "apagar" if self.action == "shutdown-pc" else "reiniciar"
        successes = 0
        errors = []
        try:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.max_workers
            ) as executor:
                futures = [
                    executor.submit(self._send_one, kiosk)
                    for kiosk in self.kiosks
                ]
                for future in concurrent.futures.as_completed(futures):
                    try:
                        _name, error = future.result()
                        if error:
                            errors.append(error)
                        else:
                            successes += 1
                    except Exception as exc:
                        errors.append(str(exc))

            summary = (
                f"Acción para {label} equipos terminada: "
                f"{successes} aceptada(s), {len(errors)} fallida(s), "
                f"de {len(self.kiosks)} equipo(s)."
            )
            if errors:
                details = "\n".join(errors[:8])
                if len(errors) > 8:
                    details += f"\n... y {len(errors) - 8} error(es) más."
                self.signals.error.emit(
                    "Resultado de la operación",
                    summary + "\n\n" + details,
                )
            else:
                self.signals.success.emit(
                    "Operación aceptada",
                    summary,
                )
        finally:
            try:
                self.signals.finished.emit()
            except RuntimeError:
                return
