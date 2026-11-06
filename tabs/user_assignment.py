"""Control reutilizable para asignar una sesión a un usuario desde su editor."""
from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QMessageBox

from action_req import AssignedSessionWorker
from const import DEFAULT_TOKEN
from css.cQDialogs import cQMsgBox
from utils import load_kiosks


class UserAssignmentController(QObject):
    """Conecta un RegisteredUserEditor con los equipos configurados."""

    def __init__(self, editor, database, threadpool, user_provider, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.database = database
        self.threadpool = threadpool
        self.user_provider = user_provider
        self._kiosks_by_host = {}
        self._equipment_snapshot = None
        self._workers = set()

        self.editor.unlock_for_user_requested.connect(self.assign_selected_user)
        self.refresh_equipment_choices()

    def refresh_equipment_choices(self):
        """Actualiza las opciones solo cuando cambia la configuración de equipos."""
        try:
            kiosks = load_kiosks()
        except (OSError, ValueError, TypeError) as exc:
            cQMsgBox.critical(
                self.editor, "Error al leer equipos",
                f"No se pudo cargar la lista de PCs registradas.\\n\\n{exc}",
            )
            kiosks = []

        snapshot = tuple(
            (kiosk.name, kiosk.host, kiosk.port) for kiosk in kiosks
        )
        if snapshot == self._equipment_snapshot:
            return

        self._equipment_snapshot = snapshot
        self._kiosks_by_host = {kiosk.host: kiosk for kiosk in kiosks}
        self.editor.set_equipment_options(kiosks)

    @staticmethod
    def _auth_headers():
        return {
            "Authorization": f"Bearer {DEFAULT_TOKEN}",
            "Content-Type": "application/json",
        }

    def assign_selected_user(self):
        user = self.user_provider()
        if not user:
            cQMsgBox.warning(
                self.editor, "Selecciona un usuario",
                "Selecciona un registro antes de asignar el equipo.",
            )
            return

        user = dict(user)
        user_type = str(user.get("tipo_usuario") or "Alumno interno").strip()
        if user_type not in ("Alumno interno", "Público en general"):
            cQMsgBox.warning(
                self.editor, "Tipo de usuario no permitido",
                "La asignación de sesión está disponible para alumnos internos "
                "y público en general.",
            )
            return

        kiosk = self._kiosks_by_host.get(self.editor.selected_equipment_host())
        if kiosk is None:
            cQMsgBox.warning(
                self.editor, "Selecciona un equipo",
                "Selecciona una PC registrada en el catálogo de equipos.",
            )
            return

        identifier = str(user.get("email") or user.get("expediente") or "").strip()
        display_name = " ".join(
            part for part in (
                str(user.get("nombres", "") or "").strip(),
                str(user.get("apellidos", "") or "").strip(),
            ) if part
        )
        if not identifier or not display_name:
            cQMsgBox.warning(
                self.editor, "Datos incompletos",
                "El usuario necesita nombre, apellidos y correo o expediente.",
            )
            return

        user_payload = {
            "display_name": display_name,
            "identifier": identifier,
            "user_type": user_type,
        }
        answer = cQMsgBox.question(
            self.editor,
            "Iniciar sesión en el equipo",
            f"Se iniciará una sesión en «{kiosk.name}» a nombre de "
            f"{display_name} ({identifier}). El acceso quedará registrado "
            "como una asignación administrativa. ¿Deseas continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        worker = AssignedSessionWorker(
            kiosk,
            user_payload,
            f"http://{kiosk.host}:{kiosk.port}",
            self._auth_headers(),
        )
        self._workers.add(worker)
        worker.signals.success.connect(
            lambda current_kiosk, _payload, title, message, record=user:
                self._on_success(current_kiosk, record, title, message)
        )
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(self._forget_worker)
        self.threadpool.start(worker)

    def _on_success(self, kiosk, user, title, message):
        try:
            self.database.record_manual_user_session(
                kiosk_name=kiosk.name,
                client_ip=kiosk.host,
                user=user,
            )
        except Exception as exc:
            cQMsgBox.critical(
                self.editor,
                "Sesión iniciada; auditoría incompleta",
                "El equipo aceptó la sesión, pero no se pudieron guardar los "
                f"eventos de auditoría en SQLite.\\n\\n{exc}",
            )
            return
        cQMsgBox.information(
            self.editor,
            title,
            message + "\\n\\nEl acceso y la asignación administrativa quedaron registrados.",
        )

    def _on_error(self, title, message):
        cQMsgBox.critical(self.editor, title, message)

    def _forget_worker(self, worker):
        self._workers.discard(worker)

    def stop(self):
        """Evita que las respuestas tardías intenten actualizar widgets cerrados."""
        self.editor.unlock_for_user_requested.disconnect(self.assign_selected_user)

    def release_workers(self):
        self._workers.clear()
