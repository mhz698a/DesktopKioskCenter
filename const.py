import sys
from dataclasses import dataclass
from pathlib import Path


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

DATA_FILE = BASE_DIR / "kiosks.json"
DEFAULT_TOKEN = "UAQinformatizacion7085"


@dataclass
class Kiosk:
    name: str
    host: str
    port: int = 7085
    token: str = DEFAULT_TOKEN
    state: str = "offline"
    locked_seconds: int | None = None
