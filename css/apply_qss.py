"""Carga hojas de estilo tanto desde el código fuente como desde el paquete compilado."""
import logging
from pathlib import Path

from const import resource_path


logger = logging.getLogger(__name__)


def apply_css_sheet(ruta_archivo: str | Path):
    """Lee una hoja de estilo empaquetada sin depender del directorio de trabajo."""
    path = resource_path(ruta_archivo)
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        logger.warning("No se pudo leer el archivo de estilos '%s'.", path, exc_info=True)
        return None
