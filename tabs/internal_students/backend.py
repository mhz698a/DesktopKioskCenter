import sqlite3

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QDialog, QMessageBox

from css.cQDialogs import cQMsgBox
from database import Database
from user_record_dialog import UserRecordDialog

FIELDS = [("nombres", "Nombres"), ("apellidos", "Apellidos"), ("email", "Correo electrónico"), ("facultad", "Facultad"), ("expediente", "Expediente")]


class InternalStudentsBackend(QObject):
    def __init__(self, view, database: Database, parent=None):
        super().__init__(parent)
        self.view, self.database = view, database
        self._selected_id = None
        self._records_by_id = {}
        self._last_records = None
        view.add_requested.connect(self.add_student)
        view.record_selection_changed.connect(self.select_student)
        view.save_requested.connect(self.save_student)
        view.delete_requested.connect(self.delete_student)
        view.revert_requested.connect(self.revert_student)
        self.refresh()

    def refresh(self, selected_id=None, preserve_editor=False):
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
            return
        self._selected_id = int(student_id)
        self.view.editor_panel.set_record(self._records_by_id[self._selected_id])

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
