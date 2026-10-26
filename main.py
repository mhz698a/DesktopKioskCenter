import sys
from threading import Thread

from flask import Flask, jsonify
from PyQt6.QtWidgets import QApplication

from wmain import MainWindow


health_app = Flask(__name__)


@health_app.get("/ping")
def ping():
    return jsonify(status="ok"), 200


def main():
    Thread(
        target=lambda: health_app.run(
            host="0.0.0.0",
            port=5000,
            debug=False,
            use_reloader=False,
            threaded=True,
        ),
        daemon=True,
    ).start()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
