import os
import sys
import ctypes
import platform
import sqlite3

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from css.cQDialogs import cQMsgBox
from database import Database
from api_server import ApiServer
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

    api_server = None
    try:
        database = Database()
        database.initialize()
        window = MainWindow(database=database)
        api_server = ApiServer(database)
        api_server.start()
    except (OSError, ValueError, sqlite3.Error) as exc:
        cQMsgBox.critical(
            None,
            "Error al iniciar DesktopKioskCenter",
            "No se pudo iniciar la base de datos o el servidor HTTP REST.\n\n"
            f"{exc}\n\n"
            "Verifique los permisos de AppData y que el puerto REST esté disponible. "
            "El puerto predeterminado es 8080; puede cambiarlo con "
            "DESKTOPKIOSKCENTER_API_PORT.",
        )
        if api_server is not None:
            api_server.stop()
        return 1

    window.show()
    try:
        return app.exec()
    finally:
        if api_server is not None:
            api_server.stop()


if __name__ == "__main__":
    raise SystemExit(main())
