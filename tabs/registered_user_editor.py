"""Panel lateral reutilizable para editar registros seleccionados."""
import re

from PyQt6.QtCore import QRegularExpression, pyqtSignal
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import QComboBox, QFormLayout, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget

from user_record_dialog import FACULTADES_UAQ, TIPOS_USUARIO, UNIVERSIDADES_QUERETARO


class RegisteredUserEditor(QWidget):
    save_requested = pyqtSignal()
    delete_requested = pyqtSignal()
    revert_requested = pyqtSignal()

    def __init__(self, kind: str, parent=None):
        super().__init__(parent)
        if kind not in ("student", "external"):
            raise ValueError("kind debe ser 'student' o 'external'")
        self.kind = kind
        self.inputs = {}
        self._original_record = None
        fields = (
            [("nombres", "Nombres"), ("apellidos", "Apellidos"),
             ("facultad", "Facultad"), ("expediente", "Expediente")]
            if kind == "student" else
            [("nombres", "Nombres"), ("apellidos", "Apellidos"),
             ("tipo_usuario", "Tipo de usuario"),
             ("universidad", "Universidad Perteneciente")]
        )
        form = QFormLayout()
        for key, label in fields:
            widget = self._create_field(key)
            self.inputs[key] = widget
            form.addRow(label + ":", widget)

        buttons = QHBoxLayout()
        self.delete_button = QPushButton("Eliminar Usuario", self)
        self.save_button = QPushButton("Guardar Cambios", self)
        self.revert_button = QPushButton("Revertir Cambios", self)
        buttons.addWidget(self.delete_button)
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.revert_button)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)
        layout.addStretch(1)
        self.delete_button.clicked.connect(lambda _checked=False: self.delete_requested.emit())
        self.save_button.clicked.connect(lambda _checked=False: self.save_requested.emit())
        self.revert_button.clicked.connect(lambda _checked=False: self.revert_requested.emit())
        self.clear_record()

    def _create_field(self, key):
        if key == "facultad":
            widget = QComboBox(self)
            widget.addItems(FACULTADES_UAQ)
            widget.setCurrentIndex(-1)
            return widget
        if key == "tipo_usuario":
            widget = QComboBox(self)
            widget.addItems(TIPOS_USUARIO)
            widget.setCurrentIndex(-1)
            widget.currentTextChanged.connect(self._on_user_type_changed)
            return widget
        if key == "universidad":
            widget = QComboBox(self)
            widget.addItems(UNIVERSIDADES_QUERETARO)
            widget.setCurrentIndex(-1)
            widget.setEnabled(False)
            return widget
        widget = QLineEdit(self)
        widget.setClearButtonEnabled(True)
        if key in ("nombres", "apellidos"):
            widget.setValidator(QRegularExpressionValidator(QRegularExpression(r"^[\p{L} ]*$"), widget))
            widget.textEdited.connect(lambda text, line=widget: self._format_proper_name(line, text))
        elif key == "expediente":
            widget.setValidator(QRegularExpressionValidator(QRegularExpression(r"^[0-9]*$"), widget))
        return widget

    @staticmethod
    def _format_proper_name(field, text):
        normalized = " ".join(
            word[:1].upper() + word[1:].lower() if word else ""
            for word in text.split(" ")
        )
        if normalized == text:
            return
        cursor = field.cursorPosition()
        field.blockSignals(True)
        try:
            field.setText(normalized)
            field.setCursorPosition(min(cursor, len(normalized)))
        finally:
            field.blockSignals(False)

    def _on_user_type_changed(self, user_type):
        university = self.inputs.get("universidad")
        if university is None:
            return
        enabled = user_type == "Estudiante Externo"
        university.setEnabled(enabled)
        if not enabled:
            university.setCurrentIndex(-1)

    def _value(self, widget):
        if isinstance(widget, QComboBox):
            return widget.currentText().strip() if widget.currentIndex() >= 0 else ""
        return widget.text().strip()

    def set_record(self, record):
        self._original_record = dict(record)
        self.setEnabled(True)
        for key, widget in self.inputs.items():
            value = str(record.get(key, "") or "")
            if isinstance(widget, QComboBox):
                index = widget.findText(value)
                widget.setCurrentIndex(index if index >= 0 else -1)
            else:
                widget.setText(value)
        if self.kind == "external":
            self._on_user_type_changed(self._value(self.inputs["tipo_usuario"]))

    def clear_record(self):
        self._original_record = None
        for widget in self.inputs.values():
            if isinstance(widget, QComboBox):
                widget.setCurrentIndex(-1)
            else:
                widget.clear()
        if self.kind == "external":
            self._on_user_type_changed("")
        self.setEnabled(False)

    def revert_changes(self):
        if self._original_record is not None:
            self.set_record(self._original_record)

    def get_record(self):
        record = {key: self._value(widget) for key, widget in self.inputs.items()}
        if record.get("tipo_usuario") != "Estudiante Externo":
            record["universidad"] = ""
        return record

    def validate_record(self):
        record = self.get_record()
        required = (
            [("nombres", "Nombres"), ("apellidos", "Apellidos"),
             ("facultad", "Facultad"), ("expediente", "Expediente")]
            if self.kind == "student" else
            [("nombres", "Nombres"), ("apellidos", "Apellidos"),
             ("tipo_usuario", "Tipo de usuario")]
        )
        for key, label in required:
            if not record.get(key):
                return False, f"El campo «{label}» es obligatorio."
        for key, label in (("nombres", "Nombres"), ("apellidos", "Apellidos")):
            if not all(character.isalpha() or character == " " for character in record[key]):
                return False, f"El campo «{label}» solo permite letras y espacios."
        if self.kind == "student" and not re.fullmatch(r"[0-9]+", record["expediente"]):
            return False, "El expediente debe contener únicamente números."
        if self.kind == "external" and record.get("tipo_usuario") == "Estudiante Externo" and not record.get("universidad"):
            return False, "Selecciona la universidad del estudiante externo."
        return True, ""
