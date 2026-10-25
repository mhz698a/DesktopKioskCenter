import os
import sys
import ctypes
import platform
import sqlite3

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from css.cQDialogs import cQMsgBox
from database import Database
from wmain import MainWindow


if platform.system() == "Windows":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "DesktopKioskCenterINF"
    )

ICON_PATH = os.path.join(os.path.dirname(sys.argv[0]), "icon.png")


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("UAQ")
    app.setApplicationName("DesktopKioskCenter")
    app.setWindowIcon(QIcon(ICON_PATH))

    try:
        database = Database()
        database.initialize()
        window = MainWindow(database=database)
    except (OSError, sqlite3.Error) as exc:
        cQMsgBox.critical(
            None,
            "Error de almacenamiento",
            "No se pudo preparar el almacenamiento en AppData.\n\n"
            f"{exc}\n\n"
            "Revise los permisos de la carpeta de datos del usuario.",
        )
        return 1

    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
