import sqlite3

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QDialog, QMessageBox

from css.cQDialogs import cQMsgBox
from database import Database
from user_record_dialog import UserRecordDialog

FIELDS = [("nombres", "Nombres"), ("apellidos", "Apellidos"), ("email", "Email"), ("tipo_usuario", "Tipo de usuario"), ("universidad", "Universidad Perteneciente")]


class ExternalUsersBackend(QObject):
    def __init__(self, view, database: Database, parent=None):
        super().__init__(parent)
        self.view, self.database = view, database
        self._selected_id = None
        self._records_by_id = {}
        view.add_requested.connect(self.add_user)
        view.record_selection_changed.connect(self.select_user)
        view.save_requested.connect(self.save_user)
        view.delete_requested.connect(self.delete_user)
        view.revert_requested.connect(self.revert_user)
        self.refresh()

    def refresh(self, selected_id=None):
        records = self.database.list_external_users()
        self._records_by_id = {int(record["id"]): record for record in records}
        self.view.set_records(records, selected_id)

    def select_user(self, user_id):
        if user_id < 0 or int(user_id) not in self._records_by_id:
            self._selected_id = None
            self.view.editor_panel.clear_record()
            return
        self._selected_id = int(user_id)
        self.view.editor_panel.set_record(self._records_by_id[self._selected_id])

    def add_user(self):
        dialog = UserRecordDialog("Agregar Usuario", FIELDS, self.view)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            new_id = self.database.add_external_user(dialog.get_record())
        except sqlite3.IntegrityError:
            cQMsgBox.warning(self.view, "Email duplicado", "Ya existe un usuario con ese email.")
            return
        except (sqlite3.Error, OSError) as exc:
            cQMsgBox.critical(self.view, "Error de base de datos", f"No se pudo guardar el usuario en SQLite.\n\n{exc}")
            return
        self.refresh(selected_id=new_id)

    def save_user(self):
        if self._selected_id is None:
            return
        valid, message = self.view.editor_panel.validate_record()
        if not valid:
            cQMsgBox.warning(self.view, "Validación", message)
            return
        try:
            updated = self.database.update_external_user(self._selected_id, self.view.editor_panel.get_record())
        except sqlite3.IntegrityError:
            cQMsgBox.warning(self.view, "Email duplicado", "Ya existe otro usuario con ese email.")
            return
        except (sqlite3.Error, OSError) as exc:
            cQMsgBox.critical(self.view, "Error de base de datos", f"No se pudieron guardar los cambios.\n\n{exc}")
            return
        if updated:
            selected_id = self._selected_id
            self.refresh(selected_id=selected_id)
            cQMsgBox.information(self.view, "Usuario actualizado", "Los cambios se guardaron correctamente.")

    def delete_user(self):
        if self._selected_id is None:
            return
        answer = cQMsgBox.question(
            self.view, "Eliminar Usuario",
            "¿Deseas eliminar el usuario seleccionado? Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.database.delete_external_user(self._selected_id)
        except (sqlite3.Error, OSError) as exc:
            cQMsgBox.critical(self.view, "Error de base de datos", f"No se pudo eliminar el usuario.\n\n{exc}")
            return
        self._selected_id = None
        self.refresh()
        cQMsgBox.information(self.view, "Usuario eliminado", "El registro se eliminó correctamente.")

    def revert_user(self):
        self.view.editor_panel.revert_changes()
