import sqlite3

from PyQt6.QtCore import QObject, QThreadPool
from PyQt6.QtWidgets import QDialog, QMessageBox

from action_req import StudentUnlockWorker
from css.cQDialogs import cQMsgBox
from database import Database
from tabs.equipment.backend import EquipmentBackend
from utils import load_kiosks
from user_record_dialog import UserRecordDialog

FIELDS = [("nombres", "Nombres"), ("apellidos", "Apellidos"), ("email", "Correo electrónico"), ("facultad", "Facultad"), ("expediente", "Expediente")]


class InternalStudentsBackend(QObject):
    def __init__(
        self, view, database: Database, parent=None, threadpool=None
    ):
        super().__init__(parent)
        self.view, self.database = view, database
        self.threadpool = threadpool or QThreadPool.globalInstance()
        self._selected_id = None
        self._closing = False
        self._workers = set()
        self._kiosks_by_host = {}
        self._records_by_id = {}
        self._last_records = None
        view.add_requested.connect(self.add_student)
        view.record_selection_changed.connect(self.select_student)
        view.save_requested.connect(self.save_student)
        view.delete_requested.connect(self.delete_student)
        view.revert_requested.connect(self.revert_student)
        view.unlock_for_student_requested.connect(self.unlock_for_student)
        self.refresh()
        self.refresh_equipment_choices()

    def refresh(self, selected_id=None, preserve_editor=False):
        if self._closing:
            return
        records = self.database.list_internal_students()
        if preserve_editor and records == self._last_records:
            return

        records_by_id = {int(record["id"]): record for record in records}
        if preserve_editor:
            selected_id = self._selected_id
            if selected_id is not None and selected_id not in records_by_id:
                self._selected_id = None
                selected_id = None
                self.view.editor_panel.clear_record()

        self._last_records = records
        self._records_by_id = records_by_id
        self.view.set_records(
            records,
            selected_id,
            emit_selection=not preserve_editor,
        )

    def select_student(self, student_id):
        if student_id < 0 or int(student_id) not in self._records_by_id:
            self._selected_id = None
            self.view.editor_panel.clear_record()
            self.view.set_student_selected(False)
            return
        self._selected_id = int(student_id)
        self.view.editor_panel.set_record(self._records_by_id[self._selected_id])
        self.view.set_student_selected(True)

    def refresh_equipment_choices(self):
        """Recarga las etiquetas registradas sin perder la selección del combo."""
        if self._closing:
            return
        try:
            kiosks = load_kiosks()
        except Exception as exc:
            cQMsgBox.critical(
                self.view, "Error al leer equipos",
                f"No se pudo cargar la lista de PCs registradas.\\n\\n{exc}",
            )
            kiosks = []
        self._kiosks_by_host = {kiosk.host: kiosk for kiosk in kiosks}
        self.view.set_equipment_options(kiosks)

    def unlock_for_student(self):
        if self._closing or self._selected_id not in self._records_by_id:
            return
        host = self.view.selected_equipment_host()
        kiosk = self._kiosks_by_host.get(host)
        if kiosk is None:
            cQMsgBox.warning(
                self.view, "Selecciona un equipo", "Selecciona una PC registrada."
            )
            return

        student = dict(self._records_by_id[self._selected_id])
        answer = cQMsgBox.question(
            self.view,
            "Desbloquear equipo para alumno",
            f"Se enviará el desbloqueo a «{kiosk.name}» para "
            f"{student.get('nombres', '')} {student.get('apellidos', '')}. "
            "Si el kiosco acepta la solicitud, el acceso se registrará a nombre "
            "del alumno y se crearán eventos de registro/desbloqueo marcados "
            "como simulación administrativa. ¿Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        worker = StudentUnlockWorker(
            kiosk, student, f"http://{kiosk.host}:{kiosk.port}",
            EquipmentBackend._auth_headers(),
        )
        self._workers.add(worker)
        worker.signals.success.connect(self.on_student_unlock_success)
        worker.signals.error.connect(self.on_student_unlock_error)
        worker.signals.finished.connect(self._forget_worker)
        self.threadpool.start(worker)

    def on_student_unlock_success(self, kiosk, student, title, message):
        if self._closing:
            return
        try:
            self.database.record_manual_student_unlock(
                kiosk_name=kiosk.name, client_ip=kiosk.host, student=student
            )
        except Exception as exc:
            cQMsgBox.critical(
                self.view, "Equipo desbloqueado; auditoría incompleta",
                f"El equipo aceptó el desbloqueo, pero no se pudieron guardar "
                f"los eventos de auditoría.\\n\\n{exc}",
            )
            return
        cQMsgBox.information(
            self.view, title,
            message + "\\n\\nEl acceso y los eventos simulados quedaron registrados.",
        )

    def on_student_unlock_error(self, title, message):
        if not self._closing:
            cQMsgBox.critical(self.view, title, message)

    def _forget_worker(self, worker):
        self._workers.discard(worker)

    def stop(self):
        self._closing = True

    def release_workers(self):
        self._workers.clear()

    def add_student(self):
        dialog = UserRecordDialog("Agregar Alumno", FIELDS, self.view)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            new_id = self.database.add_internal_student(dialog.get_record())
        except sqlite3.IntegrityError:
            cQMsgBox.warning(self.view, "Registro duplicado", "Ya existe un usuario registrado con ese correo electrónico o expediente.")
            return
        except (sqlite3.Error, OSError) as exc:
            cQMsgBox.critical(self.view, "Error de base de datos", f"No se pudo guardar el alumno en SQLite.\n\n{exc}")
            return
        self.refresh(selected_id=new_id)

    def save_student(self):
        if self._selected_id is None:
            return
        valid, message = self.view.editor_panel.validate_record()
        if not valid:
            cQMsgBox.warning(self.view, "Validación", message)
            return
        try:
            updated = self.database.update_internal_student(self._selected_id, self.view.editor_panel.get_record())
        except sqlite3.IntegrityError:
            cQMsgBox.warning(self.view, "Registro duplicado", "Ya existe otro usuario con ese correo electrónico o expediente.")
            return
        except (sqlite3.Error, OSError) as exc:
            cQMsgBox.critical(self.view, "Error de base de datos", f"No se pudieron guardar los cambios.\n\n{exc}")
            return
        if updated:
            selected_id = self._selected_id
            self.refresh(selected_id=selected_id)
            cQMsgBox.information(self.view, "Alumno actualizado", "Los cambios se guardaron correctamente.")

    def delete_student(self):
        if self._selected_id is None:
            return
        answer = cQMsgBox.question(
            self.view, "Eliminar Usuario",
            "¿Deseas eliminar el alumno seleccionado? Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.database.delete_internal_student(self._selected_id)
        except (sqlite3.Error, OSError) as exc:
            cQMsgBox.critical(self.view, "Error de base de datos", f"No se pudo eliminar el alumno.\n\n{exc}")
            return
        self._selected_id = None
        self.refresh()
        cQMsgBox.information(self.view, "Alumno eliminado", "El registro se eliminó correctamente.")

    def revert_student(self):
        self.view.editor_panel.revert_changes()
