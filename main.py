import json
import os
import sys
import requests
from dataclasses import asdict, dataclass
from pathlib import Path

from PyQt6.QtWidgets import (QApplication)
from PyQt6.QtCore import QTimer, QObject, QRunnable, QThreadPool, pyqtSignal

from wmain import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
