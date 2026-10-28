from PyQt6.QtWidgets import (
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from css.cQDialogs import cQMsgBox, cQDlg

class BulkEquipmentDialog(cQDlg):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agregar varios equipos")
        self.setMinimumWidth(430)
        self.setMaximumHeight(100)

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
        self.name_base_input.setToolTip(
            "Prefijo o nombre base para identificar a los equipos (ej. PC #)\n"
            "Ejemplo con rango 1-15: PC #1 hasta PC #15\n"
            "Se agrega al final la numeracion correspondiente."
        )
        self.ip_base_input = QLineEdit("192.168.100._", self)
        self.ip_base_input.setPlaceholderText("Ejemplo: 192.168.100._")
        self.ip_base_input.setToolTip(
            "Base de la dirección IP donde se intercalará el número del equipo\n"
            "Ejemplo con rango 1-15: 192.168.100.1 hasta 192.168.100.15\n"
            "Dejar el ultimo octeto con guion bajo para rango."
        )

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
            cQMsgBox.warning(
                self,
                "Rango inválido",
                "El valor inicial no puede ser mayor que el valor final.",
            )
            self.start_spin.setFocus()
            return
        if not values["name_base"]:
            cQMsgBox.warning(
                self, "Validación", "El nombre base es obligatorio."
            )
            self.name_base_input.setFocus()
            return
        if not values["ip_base"]:
            cQMsgBox.warning(self, "Validación", "La IP Base es obligatoria.")
            self.ip_base_input.setFocus()
            return
        super().accept()
