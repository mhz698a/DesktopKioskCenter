"""Rutas y modelos compartidos de DesktopKioskCenter.

Los recursos visuales siguen junto al programa; los datos de usuario se guardan
en APP_DATA_DIR para que no dependan del directorio de instalación.
"""
import os
import sys
from dataclasses import dataclass
from pathlib import Path


if getattr(sys, "frozen", False):
    # Directorio del ejecutable: se usa para recursos y migrar datos de versiones previas.
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent


def resource_path(relative_path: str | Path) -> Path:
    """Resuelve recursos estáticos tanto desde el código como desde PyInstaller.

    En una compilación onedir, PyInstaller coloca los recursos en sys._MEIPASS
    (normalmente la carpeta _internal), no junto al ejecutable.
    """
    bundle_dir = getattr(sys, "_MEIPASS", None)
    root = Path(bundle_dir) if bundle_dir else Path(__file__).resolve().parent
    return root / relative_path


def _get_roaming_data_root() -> Path:
    """Devuelve el directorio de datos del usuario para el sistema operativo actual."""
    if os.name == "nt":
        # En Windows se usa %APPDATA%; la alternativa cubre entornos sin esa variable.
        root = os.environ.get("APPDATA")
        return Path(root) if root else Path.home() / "AppData" / "Roaming"

    # Para desarrollo en otros sistemas se respeta XDG_DATA_HOME.
    root = os.environ.get("XDG_DATA_HOME")
    return Path(root) if root else Path.home() / ".local" / "share"


APP_DATA_DIR = _get_roaming_data_root() / "DesktopKioskCenter"
DATA_FILE = APP_DATA_DIR / "kiosks.json"
DATABASE_FILE = APP_DATA_DIR / "desktopkioskcenter.sqlite3"
DEFAULT_TOKEN = "UAQinformatizacion7085"


def ensure_app_data_dir() -> Path:
    """Crea el directorio de datos si no existe y devuelve su ruta."""
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return APP_DATA_DIR


@dataclass
class Kiosk:
    name: str
    host: str
    port: int = 7085
    token: str = DEFAULT_TOKEN
    state: str = "offline"
    locked_seconds: int | None = None
