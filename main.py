import sys

from PyQt6.QtWidgets import (QApplication)

from wmain import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("fusion")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
