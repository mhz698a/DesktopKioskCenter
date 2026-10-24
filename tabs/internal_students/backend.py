from PyQt6.QtWidgets import QDialog, QMessageBox
from PyQt6.QtCore import QObject

from const import BASE_DIR
from record_storage import load_records, save_records
from user_record_dialog import UserRecordDialog


RECORD_FILE = BASE_DIR / "internal_students.json"
FIELDS = [
    ("nombres", "Nombres"),
    ("apellidos", "Apellidos"),
    ("facultad", "Facultad"),
    ("expediente", "Expediente"),
]


class InternalStudentsBackend(QObject):
    def __init__(self, view, parent=None):
        super().__init__(parent)
        self.view = view
        self.records = load_records(RECORD_FILE, FIELDS)
        self.view.add_requested.connect(self.add_student)
        self.view.set_records(self.records)

    def add_student(self):
        dialog = UserRecordDialog("Agregar Alumno", FIELDS, self.view)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        updated = self.records + [dialog.get_record()]
        try:
            save_records(RECORD_FILE, updated)
        except OSError as exc:
            QMessageBox.critical(
                self.view, "Error al guardar", f"No se pudo guardar el alumno.\n\n{exc}"
            )
            return
        self.records = updated
        self.view.set_records(self.records)
