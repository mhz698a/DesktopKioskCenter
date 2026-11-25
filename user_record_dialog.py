"""Diálogo común para altas de alumnos, docentes, administrativos y usuarios.

El tipo de widget depende de la clave de cada campo. Esto evita duplicar diálogos
y mantiene las reglas de entrada juntas, antes de enviar datos a SQLite.
"""
import re

from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import (
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)

from css.cQDialogs import cQMsgBox, cQDlg
from user_catalogs import (
    EXTERNAL_USER_TYPE_DEFAULTS,
    FACULTY_DEFAULTS,
    INTERNAL_STAFF_TYPES,
    UNIVERSITY_DEFAULTS,
)

UNIVERSIDADES_QUERETARO = list(UNIVERSITY_DEFAULTS)
TIPOS_USUARIO = [name for name, _required in EXTERNAL_USER_TYPE_DEFAULTS]


class UserRecordDialog(cQDlg):
    def __init__(
        self, title, fields, parent=None, *, faculties=None, user_type_options=None,
        universities=None, university_required_types=None
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(520)
        self.fields = fields
        self.faculties = list(FACULTY_DEFAULTS if faculties is None else faculties)
        self.user_type_options = list(
            TIPOS_USUARIO if user_type_options is None else user_type_options
        )
        self.universities = list(
            UNIVERSIDADES_QUERETARO if universities is None else universities
        )
        if university_required_types is None:
            university_required_types = {
                name for name, required in EXTERNAL_USER_TYPE_DEFAULTS if required
            }
        self.university_required_types = {
            str(name).strip().casefold() for name in university_required_types
        }
        self.inputs = {}

        form = QFormLayout()
        for key, label in fields:
            widget = self._create_field(key)
            self.inputs[key] = widget
            form.addRow(f"{label}:", widget)

        if "tipo_usuario" in self.inputs:
            self.inputs["tipo_usuario"].currentTextChanged.connect(
                self._on_user_type_changed
            )
            self._on_user_type_changed(self.inputs["tipo_usuario"].currentText())

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _create_field(self, key):
        """Crea el widget apropiado según el significado del campo."""
        if key == "facultad":
            combo = QComboBox(self)
            combo.addItems(self.faculties)
            combo.setCurrentIndex(-1)
            return combo

        if key == "tipo_usuario":
            combo = QComboBox(self)
            combo.addItems(self.user_type_options)
            combo.setCurrentIndex(-1)
            return combo

        if key == "universidad":
            combo = QComboBox(self)
            combo.addItems(self.universities)
            combo.setCurrentIndex(-1)
            combo.setEnabled(False)
            return combo

        line_edit = QLineEdit(self)
        line_edit.setClearButtonEnabled(True)

        if key in ("nombres", "apellidos"):
            # Solo acepta letras Unicode y espacios; también cubre nombres con acentos.
            validator = QRegularExpressionValidator(
                QRegularExpression(r"^[\p{L} ]*$"),
                line_edit,
            )
            line_edit.setValidator(validator)
            line_edit.textEdited.connect(
                lambda text, field=line_edit: self._format_proper_name(field, text)
            )

        elif key in ("expediente", "numero_empleado"):
            line_edit.setValidator(
                QRegularExpressionValidator(
                    QRegularExpression(r"^[0-9]*$"),
                    line_edit,
                )
            )

        return line_edit

    @staticmethod
    def _format_proper_name(field, text):
        """Convierte cada palabra a Nombre Propio sin quitar el espacio final."""
        normalized = " ".join(
            word[:1].upper() + word[1:].lower() if word else ""
            for word in text.split(" ")
        )
        if normalized == text:
            return

        cursor_position = field.cursorPosition()
        field.blockSignals(True)
        try:
            field.setText(normalized)
            field.setCursorPosition(min(cursor_position, len(normalized)))
        finally:
            field.blockSignals(False)

    def _on_user_type_changed(self, user_type):
        university = self.inputs.get("universidad")
        if university is None:
            return

        requires_university = str(user_type or "").strip().casefold() in self.university_required_types
        university.setEnabled(requires_university)
        if not requires_university:
            university.setCurrentIndex(-1)

    def _value(self, widget):
        if isinstance(widget, QComboBox):
            return widget.currentText().strip() if widget.currentIndex() >= 0 else ""
        return widget.text().strip()

    def get_record(self):
        record = {
            key: self._value(widget)
            for key, widget in self.inputs.items()
        }
        if str(record.get("tipo_usuario", "")).strip().casefold() not in self.university_required_types:
            record["universidad"] = ""
        return record

    def accept(self):
        user_type_widget = self.inputs.get("tipo_usuario")
        user_type = self._value(user_type_widget) if user_type_widget is not None else ""
        for key, label in self.fields:
            value = self._value(self.inputs[key])

            if key == "email":
                # Email es obligatorio para cualquier tipo de usuario.
                if not value:
                    cQMsgBox.warning(
                        self, "Validación",
                        "El correo electrónico es obligatorio para todos los usuarios.",
                    )
                    self.inputs[key].setFocus()
                    return
                if value and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
                    cQMsgBox.warning(
                        self, "Validación", "Ingresa una dirección de email válida."
                    )
                    self.inputs[key].setFocus()
                    return
                continue

            if (
                key == "universidad"
                and user_type.strip().casefold() not in self.university_required_types
            ):
                continue

            if not value:
                cQMsgBox.warning(
                    self, "Validación", f"El campo «{label}» es obligatorio."
                )
                self.inputs[key].setFocus()
                return

            if key in ("nombres", "apellidos"):
                if not all(character.isalpha() or character == " " for character in value):
                    cQMsgBox.warning(
                        self, "Validación",
                        f"El campo «{label}» solo permite letras y espacios.",
                    )
                    self.inputs[key].setFocus()
                    return

            if key in ("expediente", "numero_empleado") and not re.fullmatch(r"[0-9]+", value):
                label_id = "número de empleado" if key == "numero_empleado" else "expediente"
                cQMsgBox.warning(
                    self, "Validación",
                    f"El {label_id} debe contener únicamente números.",
                )
                self.inputs[key].setFocus()
                return

        super().accept()
