from PyQt6.QtWidgets import (
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)
from css.cQDialogs import cQMsgBox, cQDlg

class UserRecordDialog(cQDlg):
    def __init__(self, title, fields, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.fields = fields
        self.inputs = {}

        form = QFormLayout()
        for key, label in fields:
            field_input = QLineEdit(self)
            field_input.setClearButtonEnabled(True)
            form.addRow(f"{label}:", field_input)
            self.inputs[key] = field_input

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

    def get_record(self):
        return {
            key: field_input.text().strip()
            for key, field_input in self.inputs.items()
        }

    def accept(self):
        for key, label in self.fields:
            if not self.inputs[key].text().strip():
                cQMsgBox.warning(
                    self,
                    "Validación",
                    f"El campo «{label}» es obligatorio.",
                )
                self.inputs[key].setFocus()
                return

        super().accept()
