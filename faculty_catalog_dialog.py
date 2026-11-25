"""Diálogo para mantener el catálogo central de facultades."""

import sqlite3

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QMessageBox,
)

from css.cQDialogs import cQDlg, cQMsgBox


class FacultyCatalogDialog(cQDlg):
    def __init__(self, database, parent=None):
        super().__init__(parent)
        self.database = database
        self.setWindowTitle("Administrar facultades")
        self.setMinimumSize(480, 420)

        self.faculty_list = QListWidget(self)
        self.name_input = QLineEdit(self)
        self.name_input.setPlaceholderText("Nombre de la facultad")

        self.add_button = QPushButton("Agregar", self)
        self.rename_button = QPushButton("Renombrar", self)
        self.delete_button = QPushButton("Eliminar", self)
        self.close_button = QPushButton("Cerrar", self)

        input_row = QHBoxLayout()
        input_row.addWidget(self.name_input, 1)
        input_row.addWidget(self.add_button)

        actions = QHBoxLayout()
        actions.addWidget(self.rename_button)
        actions.addWidget(self.delete_button)
        actions.addStretch(1)
        actions.addWidget(self.close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Este catálogo se comparte entre alumnos, docentes y administrativos.",
            self,
        ))
        layout.addWidget(self.faculty_list, 1)
        layout.addLayout(input_row)
        layout.addLayout(actions)

        self.add_button.clicked.connect(self.add_faculty)
        self.rename_button.clicked.connect(self.rename_faculty)
        self.delete_button.clicked.connect(self.delete_faculty)
        self.close_button.clicked.connect(self.accept)
        self.faculty_list.currentTextChanged.connect(self._load_selected_name)
        self.refresh()

    def refresh(self, selected_name=None):
        names = self.database.list_faculties()
        self.faculty_list.clear()
        self.faculty_list.addItems(names)
        if selected_name:
            item = self.faculty_list.findItems(
                selected_name,
                Qt.MatchFlag.MatchFixedString,
            )
            if item:
                self.faculty_list.setCurrentItem(item[0])
        if not self.faculty_list.currentItem():
            self.name_input.clear()

    def _load_selected_name(self, name):
        self.name_input.setText(name)

    def add_faculty(self):
        name = self.name_input.text().strip()
        if not name:
            cQMsgBox.warning(self, "Nombre requerido", "Escribe el nombre de la facultad.")
            self.name_input.setFocus()
            return
        try:
            added = self.database.add_faculty(name)
        except (sqlite3.Error, ValueError) as exc:
            cQMsgBox.critical(self, "Error", f"No se pudo agregar la facultad.\\n\\n{exc}")
            return
        if not added:
            cQMsgBox.information(self, "Facultad existente", "La facultad ya está en el catálogo.")
            self.refresh(name)
            return
        self.refresh(name)
        self.name_input.clear()

    def rename_faculty(self):
        selected = self.faculty_list.currentItem()
        old_name = selected.text().strip() if selected else ""
        new_name = self.name_input.text().strip()
        if not old_name:
            cQMsgBox.warning(self, "Selecciona una facultad", "Selecciona una facultad para renombrarla.")
            return
        if not new_name:
            cQMsgBox.warning(self, "Nombre requerido", "Escribe el nuevo nombre de la facultad.")
            self.name_input.setFocus()
            return
        try:
            changed = self.database.rename_faculty(old_name, new_name)
        except sqlite3.IntegrityError:
            cQMsgBox.warning(self, "Nombre duplicado", "Ya existe una facultad con ese nombre.")
            return
        except (sqlite3.Error, ValueError) as exc:
            cQMsgBox.critical(self, "Error", f"No se pudo renombrar la facultad.\\n\\n{exc}")
            return
        if changed:
            self.refresh(new_name)
            cQMsgBox.information(
                self,
                "Facultad actualizada",
                "Se actualizó el nombre en el catálogo, los usuarios registrados y el historial de accesos.",
            )

    def delete_faculty(self):
        selected = self.faculty_list.currentItem()
        name = selected.text().strip() if selected else ""
        if not name:
            cQMsgBox.warning(self, "Selecciona una facultad", "Selecciona una facultad para eliminarla.")
            return
        answer = cQMsgBox.question(
            self,
            "Eliminar facultad",
            f"¿Deseas eliminar «{name}» del catálogo? Los registros históricos se conservarán.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.database.delete_faculty(name)
        except ValueError as exc:
            cQMsgBox.warning(self, "Facultad en uso", str(exc))
            return
        except sqlite3.Error as exc:
            cQMsgBox.critical(self, "Error", f"No se pudo eliminar la facultad.\\n\\n{exc}")
            return
        self.refresh()
        self.name_input.clear()
