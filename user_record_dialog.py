"""Diálogo común para altas de alumnos y usuarios.

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


FACULTADES_UAQ = [
    "Facultad de Artes",
    "Facultad de Ciencias Naturales",
    "Facultad de Ciencias Políticas y Sociales",
    "Facultad de Contaduría y Administración",
    "Facultad de Derecho",
    "Facultad de Enfermería",
    "Facultad de Filosofía",
    "Facultad de Informática",
    "Facultad de Ingeniería",
    "Facultad de Lenguas y Letras",
    "Facultad de Medicina",
    "Facultad de Psicología y Educación",
    "Facultad de Química",
]

UNIVERSIDADES_QUERETARO = [
    "Instituto Tecnológico de Querétaro (ITQ)",
    "Universidad Tecnológica de Querétaro (UTEQ)",
    "Universidad Politécnica de Querétaro (UPQ)",
    "Universidad Aeronáutica en Querétaro (UNAQ)",
    "Universidad Nacional Autónoma de México (UNAM - Campus Juriquilla)",
    "Universidad Tecnológica de San Juan del Río (UTSJR)",
    "Universidad Politécnica de Santa Rosa Jáuregui (UPSRJ)",
    "Escuela Normal Superior de Querétaro – ENSQ",
    "Tecnológico de Monterrey (Campus Querétaro)",
    "Universidad Anáhuac (Sede Querétaro)",
    "Universidad Tecnológica de México (UNITEC)",
    "Universidad Marista de Querétaro",
    "Universidad Cuauhtémoc (Plantel Querétaro)",
    "Arkansas State University (Campus Querétaro)",
    "Universidad de Estudios Avanzados (UNEA)",
    "Universidad Tecmilenio",
    "Otra institución externa",
]

TIPOS_USUARIO = [
    "Estudiante Externo",
    "Trabajador Interno",
    "Público en general",
]


class UserRecordDialog(cQDlg):
    def __init__(self, title, fields, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(520)
        self.fields = fields
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
            combo.addItems(FACULTADES_UAQ)
            combo.setCurrentIndex(-1)
            return combo

        if key == "tipo_usuario":
            combo = QComboBox(self)
            combo.addItems(TIPOS_USUARIO)
            combo.setCurrentIndex(-1)
            return combo

        if key == "universidad":
            combo = QComboBox(self)
            combo.addItems(UNIVERSIDADES_QUERETARO)
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

        elif key == "expediente":
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

        is_external_student = user_type == "Estudiante Externo"
        university.setEnabled(is_external_student)
        if not is_external_student:
            # Para trabajador interno o público general no se conserva universidad.
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
        if record.get("tipo_usuario") != "Estudiante Externo":
            record["universidad"] = ""
        return record

    def accept(self):
        user_type = self._value(self.inputs.get("tipo_usuario"))
        for key, label in self.fields:
            value = self._value(self.inputs[key])

            if key == "email":
                # Email es opcional para estudiante externo, requerido para público general.
                if not value and user_type == "Público en general":
                    cQMsgBox.warning(
                        self, "Validación",
                        "El campo «Email» es obligatorio para Público en general.",
                    )
                    self.inputs[key].setFocus()
                    return
                if value and not re.fullmatch(r"[^@\\s]+@[^@\\s]+\\.[^@\\s]+", value):
                    cQMsgBox.warning(
                        self, "Validación", "Ingresa una dirección de email válida."
                    )
                    self.inputs[key].setFocus()
                    return
                continue

            if key == "universidad" and user_type != "Estudiante Externo":
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

            if key == "expediente" and not re.fullmatch(r"[0-9]+", value):
                cQMsgBox.warning(
                    self, "Validación",
                    "El expediente debe contener únicamente números.",
                )
                self.inputs[key].setFocus()
                return

        super().accept()
