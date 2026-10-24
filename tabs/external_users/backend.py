from PyQt6.QtWidgets import QDialog
from PyQt6.QtCore import QObject

from const import BASE_DIR
from record_storage import load_records, save_records
from user_record_dialog import UserRecordDialog
from css.cQDialogs import cQMsgBox

RECORD_FILE = BASE_DIR / "external_users.json"
FIELDS = [
    ("nombres", "Nombres"),
    ("apellidos", "Apellidos"),
    ("tipo_usuario", "Tipo de usuario"),
    ("universidad", "Universidad Perteneciente"),
]


class ExternalUsersBackend(QObject):
    def __init__(self, view, parent=None):
        super().__init__(parent)
        self.view = view
        self.records = load_records(RECORD_FILE, FIELDS)
        self.view.add_requested.connect(self.add_user)
        self.view.set_records(self.records)

    def add_user(self):
        dialog = UserRecordDialog("Agregar Usuario", FIELDS, self.view)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        updated = self.records + [dialog.get_record()]
        try:
            save_records(RECORD_FILE, updated)
        except OSError as exc:
            cQMsgBox.critical(
                self.view, "Error al guardar", f"No se pudo guardar el usuario externo.\n\n{exc}"
            )
            return
        self.records = updated
        self.view.set_records(self.records)
