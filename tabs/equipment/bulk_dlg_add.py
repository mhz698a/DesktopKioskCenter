from PyQt6.QtWidgets import (
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)

from css.cQDialogs import cQMsgBox, cQDlg
from const import DEFAULT_TOKEN, Kiosk


class KioskDialog(cQDlg):
    def __init__(self, parent=None, kiosk: Kiosk | None = None):
        super().__init__(parent)
        self.setWindowTitle("Agregar equipo" if kiosk is None else "Editar equipo")
        self.name = QLineEdit(self)
        self.host = QLineEdit(self)
        self.port = QLineEdit("7085", self)
        self.port.setReadOnly(True)
        self.setMinimumWidth(430)

        if kiosk is not None:
            self.name.setText(kiosk.name)
            self.host.setText(kiosk.host)
            self.port.setText(str(kiosk.port))

        form = QFormLayout()
        form.addRow("Nombre:", self.name)
        form.addRow("IP del cliente:", self.host)
        form.addRow("Puerto (Solo Lectura):", self.port)
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

    def get_kiosk(self) -> Kiosk:
        return Kiosk(
            name=self.name.text().strip(),
            host=self.host.text().strip(),
            port=int(self.port.text().strip() or "7085"),
            token=DEFAULT_TOKEN,
        )

    def accept(self):
        if not self.name.text().strip():
            cQMsgBox.warning(self, "Validación", "El nombre es obligatorio.")
            self.name.setFocus()
            return
        if not self.host.text().strip():
            cQMsgBox.warning(self, "Validación", "La IP o host es obligatorio.")
            self.host.setFocus()
            return
        super().accept()
