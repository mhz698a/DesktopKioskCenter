import ipaddress

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QDialog, QMessageBox

from action_req import ActionWorker
from tabs.equipment.bulk_dlg_add import KioskDialog
from const import DEFAULT_TOKEN, Kiosk
from pollstatus import PollWorker
from tabs.equipment.bulk_dialog import BulkEquipmentDialog
from utils import load_kiosks, save_kiosks
from css.cQDialogs import cQMsgBox

class EquipmentBackend(QObject):
    def __init__(self, view, threadpool, parent=None):
        super().__init__(parent)
        self.view = view
        self.threadpool = threadpool
        self.kiosks = load_kiosks()
        self.selected_index = None
        self._closing = False
        self._workers = set()

        token_changed = False
        for kiosk in self.kiosks:
            if kiosk.token != DEFAULT_TOKEN:
                kiosk.token = DEFAULT_TOKEN
                token_changed = True
        if token_changed:
            try:
                save_kiosks(self.kiosks)
            except OSError:
                pass

        self.view.add_single_requested.connect(self.add_single)
        self.view.add_multiple_requested.connect(self.add_multiple)
        self.view.selection_changed.connect(self.select_equipment)
        self.view.lock_requested.connect(lambda: self.send_selected_action("lock"))
        self.view.unlock_requested.connect(lambda: self.send_selected_action("unlock"))
        self.view.delete_requested.connect(self.delete_selected)
        self.view.save_requested.connect(self.save_selected)
        self.view.revert_requested.connect(self.revert_selected)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_status)
        self.timer.start(3000)

        self.refresh_table()
        self.poll_status()

    @staticmethod
    def _state_label(state):
        return {
            "locked": "Bloqueado",
            "unlocked": "Desbloqueado",
            "offline": "Sin conexión",
            "error": "Error",
        }.get(state, state)

    @staticmethod
    def _auth_headers():
        return {
            "Authorization": f"Bearer {DEFAULT_TOKEN}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _base_url(kiosk):
        return f"http://{kiosk.host}:{kiosk.port}"

    def refresh_table(self, selected_index=None):
        self.selected_index = selected_index
        self.view.set_equipment_rows(self.kiosks, selected_index)
        self.select_equipment(
            selected_index
            if selected_index is not None and 0 <= selected_index < len(self.kiosks)
            else -1
        )

    def select_equipment(self, index):
        if self._closing:
            return
        if not 0 <= index < len(self.kiosks):
            self.selected_index = None
            self.view.set_editor_enabled(False)
            self.view.clear_editor()
            return

        self.selected_index = index
        self.view.set_editor_enabled(True)
        self.view.set_editor_values(self.kiosks[index])

    def revert_selected(self):
        index = self.selected_index
        if index is None or not 0 <= index < len(self.kiosks):
            return
        self.view.set_editor_values(self.kiosks[index])

    def add_single(self):
        if self._closing:
            return
        dialog = KioskDialog(self.view)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.kiosks.append(dialog.get_kiosk())
        try:
            save_kiosks(self.kiosks)
        except OSError as exc:
            self.kiosks.pop()
            cQMsgBox.critical(
                self.view, "Error al guardar", f"No se pudo guardar el equipo.\n\n{exc}"
            )
            return
        self.refresh_table(selected_index=len(self.kiosks) - 1)

    @staticmethod
    def _ip_prefix(ip_base):
        value = ip_base.strip()
        if value.endswith("_"):
            value = value[:-1]
        if not value.endswith("."):
            raise ValueError(
                "La IP Base debe terminar en punto o guion bajo, por ejemplo 192.168.100._."
            )

        octets = value[:-1].split(".")
        if len(octets) != 3:
            raise ValueError(
                "La IP Base debe contener los primeros tres octetos, por ejemplo 192.168.100._."
            )
        for octet in octets:
            if not octet.isdigit() or not 0 <= int(octet) <= 255:
                raise ValueError("La IP Base contiene un octeto inválido.")
        return value

    def add_multiple(self):
        if self._closing:
            return
        dialog = BulkEquipmentDialog(self.view)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        values = dialog.get_values()
        start = values["start"]
        end = values["end"]
        name_base = values["name_base"]
        try:
            ip_prefix = self._ip_prefix(values["ip_base"])
            new_kiosks = [
                Kiosk(
                    name=f"{name_base}{number}",
                    host=str(ipaddress.IPv4Address(f"{ip_prefix}{number}")),
                    port=7085,
                    token=DEFAULT_TOKEN,
                )
                for number in range(start, end + 1)
            ]
        except ValueError as exc:
            cQMsgBox.warning(self.view, "IP Base inválida", str(exc))
            return

        existing_names = {kiosk.name.strip().casefold() for kiosk in self.kiosks}
        existing_hosts = {kiosk.host.strip() for kiosk in self.kiosks}
        new_names = [kiosk.name.casefold() for kiosk in new_kiosks]
        new_hosts = [kiosk.host for kiosk in new_kiosks]

        if len(set(new_names)) != len(new_names):
            cQMsgBox.warning(
                self.view, "Rango duplicado", "El rango genera nombres repetidos."
            )
            return
        if len(set(new_hosts)) != len(new_hosts):
            cQMsgBox.warning(
                self.view, "Rango duplicado", "El rango genera direcciones IP repetidas."
            )
            return
        if any(name in existing_names for name in new_names):
            cQMsgBox.warning(
                self.view,
                "Equipo duplicado",
                "Uno o más nombres ya existen. No se agregó ningún equipo.",
            )
            return
        if any(host in existing_hosts for host in new_hosts):
            cQMsgBox.warning(
                self.view,
                "IP duplicada",
                "Una o más direcciones IP ya existen. No se agregó ningún equipo.",
            )
            return

        old_length = len(self.kiosks)
        self.kiosks.extend(new_kiosks)
        try:
            save_kiosks(self.kiosks)
        except OSError as exc:
            del self.kiosks[old_length:]
            cQMsgBox.critical(
                self.view,
                "Error al guardar",
                f"No se pudieron guardar los equipos.\n\n{exc}",
            )
            return
        self.refresh_table(selected_index=len(self.kiosks) - 1)

    def save_selected(self):
        index = self.selected_index
        if index is None or not 0 <= index < len(self.kiosks):
            return

        name, host = self.view.get_editor_values()
        if not name:
            cQMsgBox.warning(self.view, "Validación", "El nombre es obligatorio.")
            self.view.name_input.setFocus()
            return
        if not host:
            cQMsgBox.warning(self.view, "Validación", "La IP o host es obligatorio.")
            self.view.host_input.setFocus()
            return

        original = self.kiosks[index]
        updated = Kiosk(
            name=name,
            host=host,
            port=original.port,
            token=DEFAULT_TOKEN,
            state=original.state,
            locked_seconds=original.locked_seconds,
        )
        self.kiosks[index] = updated
        try:
            save_kiosks(self.kiosks)
        except OSError as exc:
            self.kiosks[index] = original
            cQMsgBox.critical(
                self.view,
                "Error al guardar",
                f"No se pudieron guardar los cambios.\n\n{exc}",
            )
            return
        self.refresh_table(selected_index=index)

    def delete_selected(self):
        index = self.selected_index
        if index is None or not 0 <= index < len(self.kiosks):
            return
        kiosk = self.kiosks[index]
        answer = cQMsgBox.question(
            self.view,
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
            cQMsgBox.critical(
                self.view,
                "Error al guardar",
                f"No se pudo eliminar el equipo.\n\n{exc}",
            )
            return
        next_index = min(index, len(self.kiosks) - 1) if self.kiosks else None
        self.refresh_table(selected_index=next_index)

    def send_selected_action(self, action):
        index = self.selected_index
        if self._closing or index is None or not 0 <= index < len(self.kiosks):
            return
        kiosk = self.kiosks[index]
        worker = ActionWorker(
            kiosk, action, self._base_url(kiosk), self._auth_headers()
        )
        self._workers.add(worker)
        worker.signals.error.connect(self.on_action_error)
        worker.signals.finished.connect(
            lambda *_args, current=worker: self._forget_worker(current)
        )
        self.threadpool.start(worker)

    def on_action_error(self, title, message):
        if not self._closing:
            cQMsgBox.critical(self.view, title, message)

    def poll_status(self):
        if self._closing:
            return
        for index, kiosk in enumerate(self.kiosks):
            worker = PollWorker(
                index, kiosk, self._base_url(kiosk), self._auth_headers()
            )
            self._workers.add(worker)
            worker.signals.finished.connect(self.on_poll_finished)
            worker.signals.finished.connect(
                lambda *_args, current=worker: self._forget_worker(current)
            )
            self.threadpool.start(worker)

    def on_poll_finished(self, index, new_state, new_seconds):
        if self._closing or not 0 <= index < len(self.kiosks):
            return
        kiosk = self.kiosks[index]
        kiosk.state = new_state
        kiosk.locked_seconds = new_seconds
        self.view.update_equipment_status(index, kiosk)

    def _forget_worker(self, worker):
        self._workers.discard(worker)

    def stop(self):
        self._closing = True
        self.timer.stop()

    def release_workers(self):
        self._workers.clear()
