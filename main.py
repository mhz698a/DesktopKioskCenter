import os, sys
import ctypes
import platform
from PyQt6.QtWidgets import (QApplication)
from PyQt6.QtGui import QIcon
from wmain import MainWindow

if platform.system() == "Windows":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("DesktopKioskCenterINF")

ICON_PATH = os.path.join(os.path.dirname(sys.argv[0]), "icon.png")

def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("UAQ")
    app.setApplicationName("DesktopKioskCenter")
    app.setWindowIcon(QIcon(ICON_PATH))
    window = MainWindow()
    window.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
