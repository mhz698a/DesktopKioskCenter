import platform
from PyQt6.QtWidgets import QDialog, QMessageBox
import pywinstyles
import platform

class cQDlg(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def showEvent(self, event):
        if platform.system() == "Windows":
            pywinstyles.apply_style(self, "dark")
        super().showEvent(event)

import platform
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import Qt
import pywinstyles

class cQMsgBox(QMessageBox):
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def showEvent(self, event):
        super().showEvent(event)
        if platform.system() == "Windows":
            self._aplicar_tema_oscuro()

    def _aplicar_tema_oscuro(self):
        try:
            pywinstyles.apply_style(self, "dark")
            self.update()
        except Exception:
            pass

    # ==================================================================
    # MÉTODOS ESTÁTICOS CORREGIDOS (Para usarlos sin instanciar la clase)
    # ==================================================================
    @staticmethod
    def _crear_y_ejecutar(parent, title, text, icon, buttons=QMessageBox.StandardButton.Ok, default_button=QMessageBox.StandardButton.NoButton):
        """Helper interno para no repetir código"""
        msg = cQMsgBox(parent)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(icon)
        msg.setStandardButtons(buttons)
        if default_button != QMessageBox.StandardButton.NoButton:
            msg.setDefaultButton(default_button)
        return msg.exec()

    @classmethod
    def critical(cls, parent, title, text, buttons=QMessageBox.StandardButton.Ok, default_button=QMessageBox.StandardButton.NoButton):
        return cls._crear_y_ejecutar(parent, title, text, QMessageBox.Icon.Critical, buttons, default_button)

    @classmethod
    def warning(cls, parent, title, text, buttons=QMessageBox.StandardButton.Ok, default_button=QMessageBox.StandardButton.NoButton):
        return cls._crear_y_ejecutar(parent, title, text, QMessageBox.Icon.Warning, buttons, default_button)

    @classmethod
    def information(cls, parent, title, text, buttons=QMessageBox.StandardButton.Ok, default_button=QMessageBox.StandardButton.NoButton):
        return cls._crear_y_ejecutar(parent, title, text, QMessageBox.Icon.Information, buttons, default_button)

    @classmethod
    def question(cls, parent, title, text, buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, default_button=QMessageBox.StandardButton.NoButton):
        return cls._crear_y_ejecutar(parent, title, text, QMessageBox.Icon.Question, buttons, default_button)
