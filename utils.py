"""Utilidades pequeñas para persistir la configuración de los kioscos."""
import json
import logging
import shutil
from dataclasses import asdict

from const import APP_DATA_DIR, BASE_DIR, DATA_FILE, Kiosk, ensure_app_data_dir


logger = logging.getLogger(__name__)


def _migrate_legacy_kiosk_file() -> None:
    """Copia kiosks.json del directorio de la aplicación a AppData una sola vez.

    La migración solo se intenta cuando el archivo nuevo todavía no existe. Así
    un archivo AppData ya utilizado no se sobrescribe con datos antiguos.
    """
    legacy_file = BASE_DIR / "kiosks.json"
    if DATA_FILE.exists() or not legacy_file.exists():
        return

    try:
        ensure_app_data_dir()
        if legacy_file.resolve() != DATA_FILE.resolve():
            shutil.copy2(legacy_file, DATA_FILE)
    except OSError:
        logger.exception("No se pudo migrar kiosks.json a AppData.")


def load_kiosks() -> list[Kiosk]:
    """Carga kioscos desde AppData, migrando el archivo antiguo si hace falta."""
    ensure_app_data_dir()
    _migrate_legacy_kiosk_file()

    if not DATA_FILE.exists():
        return []

    try:
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            logger.warning("El contenido de %s no es una lista JSON.", DATA_FILE)
            return []

        kiosks = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            try:
                kiosks.append(Kiosk(**item))
            except TypeError:
                # Ignora filas de una versión antigua con campos desconocidos o faltantes.
                logger.warning("Se omitió una entrada inválida en %s.", DATA_FILE)
        return kiosks
    except (OSError, ValueError):
        logger.exception("No se pudo leer la configuración de kioscos.")
        return []


def save_kiosks(kiosks: list[Kiosk]) -> None:
    """Guarda kiosks.json de forma atómica dentro de AppData."""
    ensure_app_data_dir()
    temporary_file = DATA_FILE.with_suffix(DATA_FILE.suffix + ".tmp")
    payload = [asdict(kiosk) for kiosk in kiosks]
    temporary_file.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary_file.replace(DATA_FILE)


def format_duration(seconds: int | None) -> str:
    """Convierte segundos a HH:MM:SS; representa valores desconocidos con una raya."""
    if seconds is None:
        return "—"

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
