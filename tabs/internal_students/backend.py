"""Backend de alumnos internos: coordina el formulario, la vista y SQLite."""
import sqlite3

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QDialog

from css.cQDialogs import cQMsgBox
from database import Database
from user_record_dialog import UserRecordDialog


FIELDS = [
    ("nombres", "Nombres"),
    ("apellidos", "Apellidos"),
    ("facultad", "Facultad"),
    ("expediente", "Expediente"),
]


class InternalStudentsBackend(QObject):
    def __init__(self, view, database: Database, parent=None):
        super().__init__(parent)
        self.view = view
        self.database = database
        self.view.add_requested.connect(self.add_student)
        self.refresh()

    def refresh(self):
        """Consulta SQLite y actualiza la tabla."""
        self.view.set_records(self.database.list_internal_students())

    def add_student(self):
        dialog = UserRecordDialog("Agregar Alumno", FIELDS, self.view)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            self.database.add_internal_student(dialog.get_record())
        except sqlite3.IntegrityError:
            cQMsgBox.warning(
                self.view,
                "Expediente duplicado",
                "Ya existe un alumno registrado con ese expediente.",
            )
            return
        except (sqlite3.Error, OSError) as exc:
            cQMsgBox.critical(
                self.view,
                "Error de base de datos",
                f"No se pudo guardar el alumno en SQLite.\n\n{exc}",
            )
            return

        self.refresh()
