import json
from dataclasses import asdict

from const import DATA_FILE, Kiosk

def load_kiosks() -> list[Kiosk]:
    if not DATA_FILE.exists():
        return []

    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        return [Kiosk(**item) for item in data]
    except (OSError, ValueError, TypeError):
        return []


def save_kiosks(kiosks: list[Kiosk]) -> None:
    payload = [asdict(kiosk) for kiosk in kiosks]
    DATA_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "—"

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"