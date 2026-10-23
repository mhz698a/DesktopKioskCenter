import os, sys
from pathlib import Path
from dataclasses import dataclass

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

DATA_FILE = BASE_DIR / "kiosks.json"

DEFAULT_TOKEN = os.getenv("DESKTOPKIOSK_API_TOKEN", "UAQinformatizacion7085")

@dataclass
class Kiosk:
    name: str
    host: str
    port: int = 7085
    token: str = ""
    state: str = "offline"
    locked_seconds: int | None = None
