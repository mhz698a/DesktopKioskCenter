from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class BulkEquipmentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agregar varios equipos")
        self.setMinimumWidth(430)

        range_widget = QWidget(self)
        range_layout = QHBoxLayout(range_widget)
        range_layout.setContentsMargins(0, 0, 0, 0)

        self.start_spin = QSpinBox(range_widget)
        self.start_spin.setRange(1, 254)
        self.start_spin.setValue(1)
        self.end_spin = QSpinBox(range_widget)
        self.end_spin.setRange(1, 254)
        self.end_spin.setValue(3)

        range_layout.addWidget(QLabel("Desde:", range_widget))
        range_layout.addWidget(self.start_spin)
        range_layout.addSpacing(12)
        range_layout.addWidget(QLabel("Hasta:", range_widget))
        range_layout.addWidget(self.end_spin)

        self.name_base_input = QLineEdit("PC #", self)
        self.name_base_input.setPlaceholderText("Ejemplo: PC #")
        self.ip_base_input = QLineEdit("192.168.100._", self)
        self.ip_base_input.setPlaceholderText("Ejemplo: 192.168.100._")

        form = QFormLayout()
        form.addRow("Rango de equipos:", range_widget)
        form.addRow("Nombre base:", self.name_base_input)
        form.addRow("IP Base:", self.ip_base_input)

        buttons = QDialogButtonBox(self)
        add_button = buttons.addButton(
            "Agregar", QDialogButtonBox.ButtonRole.AcceptRole
        )
        cancel_button = buttons.addButton(
            "Cancelar", QDialogButtonBox.ButtonRole.RejectRole
        )
        add_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def get_values(self):
        return {
            "start": self.start_spin.value(),
            "end": self.end_spin.value(),
            "name_base": self.name_base_input.text().strip(),
            "ip_base": self.ip_base_input.text().strip(),
        }

    def accept(self):
        values = self.get_values()
        if values["start"] > values["end"]:
            QMessageBox.warning(
                self,
                "Rango inválido",
                "El valor inicial no puede ser mayor que el valor final.",
            )
            self.start_spin.setFocus()
            return
        if not values["name_base"]:
            QMessageBox.warning(
                self, "Validación", "El nombre base es obligatorio."
            )
            self.name_base_input.setFocus()
            return
        if not values["ip_base"]:
            QMessageBox.warning(self, "Validación", "La IP Base es obligatoria.")
            self.ip_base_input.setFocus()
            return
        super().accept()
