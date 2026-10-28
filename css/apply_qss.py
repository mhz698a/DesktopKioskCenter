from pathlib import Path

def apply_css_sheet(ruta_archivo):
    APP_DIR = Path(__file__).resolve().parent.parent.as_posix()
    try:
        with open(f"{APP_DIR}/{ruta_archivo}", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Advertencia: No se encontró el archivo de estilos en '{ruta_archivo}'")
        return None
