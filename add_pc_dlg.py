from PyQt6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget
)
from const import Kiosk, DEFAULT_TOKEN

class KioskDialog(QDialog):
    def __init__(self, parent=None, kiosk: Kiosk | None = None):
        super().__init__(parent)
        self.setWindowTitle("Editar equipo" if kiosk else "Agregar equipo")

        self.name = QLineEdit()
        self.host = QLineEdit()
        self.port = QLineEdit("7085")
        self.token = QLineEdit()

        if kiosk:
            self.name.setText(kiosk.name)
            self.host.setText(kiosk.host)
            self.port.setText(str(kiosk.port))
            self.token.setText(kiosk.token)

        form = QFormLayout()
        form.addRow("Nombre:", self.name)
        form.addRow("IP / Host:", self.host)
        form.addRow("Puerto:", self.port)
        form.addRow("Token:", self.token)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
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
            token=self.token.text().strip(),
        )

    def accept(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "Validación", "El nombre es obligatorio.")
            return

        if not self.host.text().strip():
            QMessageBox.warning(self, "Validación", "La IP o host es obligatorio.")
            return

        try:
            port = int(self.port.text().strip())
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Validación", "El puerto debe ser un entero entre 1 y 65535.")
            return

        if not self.token.text().strip():
            self.token.setText(DEFAULT_TOKEN)

        super().accept()
