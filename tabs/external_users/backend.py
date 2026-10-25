"""Backend de usuarios externos y público en general: SQLite + presentación."""
import sqlite3

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QDialog

from css.cQDialogs import cQMsgBox
from database import Database
from user_record_dialog import UserRecordDialog


FIELDS = [
    ("nombres", "Nombres"),
    ("apellidos", "Apellidos"),
    ("tipo_usuario", "Tipo de usuario"),
    ("universidad", "Universidad Perteneciente"),
]


class ExternalUsersBackend(QObject):
    def __init__(self, view, database: Database, parent=None):
        super().__init__(parent)
        self.view = view
        self.database = database
        self.view.add_requested.connect(self.add_user)
        self.refresh()

    def refresh(self):
        """Consulta SQLite y actualiza la tabla."""
        self.view.set_records(self.database.list_external_users())

    def add_user(self):
        dialog = UserRecordDialog("Agregar Usuario", FIELDS, self.view)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            self.database.add_external_user(dialog.get_record())
        except (sqlite3.Error, OSError) as exc:
            cQMsgBox.critical(
                self.view,
                "Error de base de datos",
                f"No se pudo guardar el usuario en SQLite.\n\n{exc}",
            )
            return

        self.refresh()
