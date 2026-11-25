"""Administración persistente de tipos externos y universidades."""

import sqlite3

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from css.cQDialogs import cQDlg, cQMsgBox


class ExternalUserCatalogDialog(cQDlg):
    """Editor de los combos de tipo de usuario y universidad."""

    def __init__(self, database, parent=None):
        super().__init__(parent)
        self.database = database
        self.setWindowTitle("Administrar tipos de usuario y universidades")
        self.setMinimumSize(680, 500)

        tabs = QTabWidget(self)
        tabs.addTab(self._build_user_type_tab(), "Tipos de usuario")
        tabs.addTab(self._build_university_tab(), "Universidades")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Los cambios se guardan en la base de datos de AppData y se comparten "
            "con los kioscos al consultar el servidor central.",
            self,
        ))
        layout.addWidget(tabs, 1)
        close_button = QPushButton("Cerrar", self)
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.refresh_user_types()
        self.refresh_universities()

    def _build_user_type_tab(self):
        page = QWidget(self)
        self.type_list = QListWidget(page)
        self.type_name = QLineEdit(page)
        self.type_name.setPlaceholderText("Nombre del tipo de usuario")
        self.type_requires_university = QCheckBox(
            "Este tipo requiere seleccionar una universidad", page
        )

        self.type_add_button = QPushButton("Agregar", page)
        self.type_save_button = QPushButton("Guardar cambios", page)
        self.type_delete_button = QPushButton("Eliminar", page)

        actions = QHBoxLayout()
        actions.addWidget(self.type_add_button)
        actions.addWidget(self.type_save_button)
        actions.addWidget(self.type_delete_button)

        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(
            "Define las opciones del combo Tipo de usuario. El requisito de "
            "universidad se configura por cada tipo.",
            page,
        ))
        layout.addWidget(self.type_list, 1)
        layout.addWidget(self.type_name)
        layout.addWidget(self.type_requires_university)
        layout.addLayout(actions)

        self.type_list.currentItemChanged.connect(self._select_user_type)
        self.type_add_button.clicked.connect(self.add_user_type)
        self.type_save_button.clicked.connect(self.save_user_type)
        self.type_delete_button.clicked.connect(self.delete_user_type)
        return page

    def _build_university_tab(self):
        page = QWidget(self)
        self.university_list = QListWidget(page)
        self.university_name = QLineEdit(page)
        self.university_name.setPlaceholderText("Nombre de la universidad")

        self.university_add_button = QPushButton("Agregar", page)
        self.university_save_button = QPushButton("Guardar cambios", page)
        self.university_delete_button = QPushButton("Eliminar", page)

        actions = QHBoxLayout()
        actions.addWidget(self.university_add_button)
        actions.addWidget(self.university_save_button)
        actions.addWidget(self.university_delete_button)

        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(
            "El catálogo se comparte entre todos los tipos de usuario que "
            "requieren una universidad.",
            page,
        ))
        layout.addWidget(self.university_list, 1)
        layout.addWidget(self.university_name)
        layout.addLayout(actions)

        self.university_list.currentItemChanged.connect(self._select_university)
        self.university_add_button.clicked.connect(self.add_university)
        self.university_save_button.clicked.connect(self.save_university)
        self.university_delete_button.clicked.connect(self.delete_university)
        return page

    def refresh_user_types(self, selected_name=None):
        self.type_list.clear()
        for item in self.database.list_external_user_types():
            row = QListWidgetItem(item["name"])
            row.setData(Qt.ItemDataRole.UserRole, bool(item["requires_university"]))
            self.type_list.addItem(row)
        self._select_list_item(self.type_list, selected_name)
        if not self.type_list.currentItem():
            self.type_name.clear()
            self.type_requires_university.setChecked(False)

    def refresh_universities(self, selected_name=None):
        self.university_list.clear()
        self.university_list.addItems(self.database.list_universities())
        self._select_list_item(self.university_list, selected_name)
        if not self.university_list.currentItem():
            self.university_name.clear()

    @staticmethod
    def _select_list_item(widget, value):
        if not value:
            return
        matches = widget.findItems(value, Qt.MatchFlag.MatchFixedString)
        if matches:
            widget.setCurrentItem(matches[0])

    def _select_user_type(self, current, _previous=None):
        self.type_name.setText(current.text() if current is not None else "")
        self.type_requires_university.setChecked(
            bool(current.data(Qt.ItemDataRole.UserRole)) if current is not None else False
        )

    def _select_university(self, current, _previous=None):
        self.university_name.setText(current.text() if current is not None else "")

    def add_user_type(self):
        name = self.type_name.text().strip()
        if not name:
            cQMsgBox.warning(self, "Nombre requerido", "Escribe el tipo de usuario.")
            self.type_name.setFocus()
            return
        try:
            added = self.database.add_external_user_type(
                name, self.type_requires_university.isChecked()
            )
        except (sqlite3.Error, ValueError) as exc:
            cQMsgBox.critical(self, "Error", f"No se pudo agregar el tipo de usuario.\\n\\n{exc}")
            return
        if not added:
            cQMsgBox.information(self, "Tipo existente", "Ese tipo ya está en el catálogo.")
            self.refresh_user_types(name)
            return
        self.refresh_user_types(name)
        self.type_name.clear()
        self.type_requires_university.setChecked(False)

    def save_user_type(self):
        selected = self.type_list.currentItem()
        old_name = selected.text().strip() if selected else ""
        new_name = self.type_name.text().strip()
        if not old_name:
            cQMsgBox.warning(self, "Selecciona un tipo", "Selecciona un tipo para guardar sus cambios.")
            return
        if not new_name:
            cQMsgBox.warning(self, "Nombre requerido", "Escribe el nombre del tipo de usuario.")
            self.type_name.setFocus()
            return
        try:
            if old_name.casefold() != new_name.casefold():
                self.database.rename_external_user_type(old_name, new_name)
            self.database.set_external_user_type_requires_university(
                new_name, self.type_requires_university.isChecked()
            )
        except sqlite3.IntegrityError:
            cQMsgBox.warning(self, "Tipo duplicado", "Ya existe un tipo con ese nombre.")
            return
        except (sqlite3.Error, ValueError) as exc:
            cQMsgBox.warning(self, "No se pudieron guardar los cambios", str(exc))
            return
        self.refresh_user_types(new_name)
        cQMsgBox.information(
            self,
            "Tipo actualizado",
            "El tipo y sus reglas se guardaron. Los registros existentes conservaron su historial.",
        )

    def delete_user_type(self):
        selected = self.type_list.currentItem()
        name = selected.text().strip() if selected else ""
        if not name:
            cQMsgBox.warning(self, "Selecciona un tipo", "Selecciona un tipo para eliminarlo.")
            return
        answer = cQMsgBox.question(
            self,
            "Eliminar tipo de usuario",
            f"¿Deseas eliminar «{name}» del catálogo? No se eliminarán registros históricos.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.database.delete_external_user_type(name)
        except ValueError as exc:
            cQMsgBox.warning(self, "Tipo en uso", str(exc))
            return
        except sqlite3.Error as exc:
            cQMsgBox.critical(self, "Error", f"No se pudo eliminar el tipo.\\n\\n{exc}")
            return
        self.refresh_user_types()

    def add_university(self):
        name = self.university_name.text().strip()
        if not name:
            cQMsgBox.warning(self, "Nombre requerido", "Escribe el nombre de la universidad.")
            self.university_name.setFocus()
            return
        try:
            added = self.database.add_university(name)
        except (sqlite3.Error, ValueError) as exc:
            cQMsgBox.critical(self, "Error", f"No se pudo agregar la universidad.\\n\\n{exc}")
            return
        if not added:
            cQMsgBox.information(self, "Universidad existente", "Esa universidad ya está en el catálogo.")
            self.refresh_universities(name)
            return
        self.refresh_universities(name)
        self.university_name.clear()

    def save_university(self):
        selected = self.university_list.currentItem()
        old_name = selected.text().strip() if selected else ""
        new_name = self.university_name.text().strip()
        if not old_name:
            cQMsgBox.warning(self, "Selecciona una universidad", "Selecciona una universidad para renombrarla.")
            return
        if not new_name:
            cQMsgBox.warning(self, "Nombre requerido", "Escribe el nombre de la universidad.")
            self.university_name.setFocus()
            return
        try:
            changed = self.database.rename_university(old_name, new_name)
        except sqlite3.IntegrityError:
            cQMsgBox.warning(self, "Universidad duplicada", "Ya existe una universidad con ese nombre.")
            return
        except (sqlite3.Error, ValueError) as exc:
            cQMsgBox.critical(self, "Error", f"No se pudo renombrar la universidad.\\n\\n{exc}")
            return
        if changed:
            self.refresh_universities(new_name)
            cQMsgBox.information(
                self,
                "Universidad actualizada",
                "Se actualizó el nombre en usuarios registrados y en el historial de accesos.",
            )

    def delete_university(self):
        selected = self.university_list.currentItem()
        name = selected.text().strip() if selected else ""
        if not name:
            cQMsgBox.warning(self, "Selecciona una universidad", "Selecciona una universidad para eliminarla.")
            return
        answer = cQMsgBox.question(
            self,
            "Eliminar universidad",
            f"¿Deseas eliminar «{name}» del catálogo? Los registros históricos se conservarán.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.database.delete_university(name)
        except ValueError as exc:
            cQMsgBox.warning(self, "Universidad en uso", str(exc))
            return
        except sqlite3.Error as exc:
            cQMsgBox.critical(self, "Error", f"No se pudo eliminar la universidad.\\n\\n{exc}")
            return
        self.refresh_universities()
