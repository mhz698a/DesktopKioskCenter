from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from const import DEFAULT_TOKEN, Kiosk


class KioskDialog(QDialog):
    def __init__(self, parent=None, kiosk: Kiosk | None = None):
        super().__init__(parent)
        self.setWindowTitle("Agregar equipo" if kiosk is None else "Editar equipo")
        self.name = QLineEdit(self)
        self.host = QLineEdit(self)
        self.port = QLineEdit("7085", self)
        if kiosk is not None:
            self.name.setText(kiosk.name)
            self.host.setText(kiosk.host)
            self.port.setText(str(kiosk.port))

        form = QFormLayout()
        form.addRow("Nombre:", self.name)
        form.addRow("IP / Host:", self.host)
        form.addRow("Puerto:", self.port)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
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
            QMessageBox.warning(self, "Validación", "El nombre es obligatorio.")
            self.name.setFocus()
            return
        if not self.host.text().strip():
            QMessageBox.warning(self, "Validación", "La IP o host es obligatorio.")
            self.host.setFocus()
            return
        try:
            port = int(self.port.text().strip())
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Validación", "El puerto debe ser un entero entre 1 y 65535.")
            self.port.setFocus()
            return
        super().accept()
