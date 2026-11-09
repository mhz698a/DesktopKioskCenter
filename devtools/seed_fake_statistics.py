"""Genera datos de demostración para probar la pestaña Estadísticas.

Ejecuta desde la raíz del repositorio:
    python devtools/seed_fake_statistics.py

Los registros usan el prefijo DEMO_STATS y se guardan en la base SQLite de
AppData usada por DesktopKioskCenter. Al repetir el script solo elimina los
registros de demostración anteriores; conserva los accesos reales.
Este módulo está excluido del empaquetado de producción en main.spec.
"""
from __future__ import annotations

import random
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import Database


DEMO_PREFIX = "DEMO_STATS"
UNIVERSITIES = (
    "Universidad Tecnológica de Querétaro",
    "Universidad Politécnica de Querétaro",
    "Tecnológico de Monterrey",
    "Universidad Autónoma de Querétaro",
    "Universidad Marista de Querétaro",
    "Universidad Nacional Autónoma de México",
)
FACULTIES = (
    "Facultad de Informática",
    "Facultad de Ingeniería",
    "Facultad de Contaduría y Administración",
    "Facultad de Ciencias Políticas y Sociales",
    "Facultad de Química",
)
PEOPLE = (
    ("Andrea", "López"),
    ("Daniel", "Hernández"),
    ("Mariana", "García"),
    ("Carlos", "Ramírez"),
    ("Fernanda", "Torres"),
    ("Diego", "Sánchez"),
    ("Valeria", "Martínez"),
    ("Emiliano", "Pérez"),
    ("Camila", "Flores"),
    ("Santiago", "Morales"),
)


def remove_previous_demo_data(database: Database) -> tuple[int, int]:
    """Elimina solamente las filas que pertenecen al generador de demostración."""
    with database.connection() as connection:
        access_cursor = connection.execute(
            "DELETE FROM access_logs WHERE kiosk_name LIKE ?",
            (f"{DEMO_PREFIX}:%",),
        )
        login_cursor = connection.execute(
            "DELETE FROM received_logins WHERE kiosk_name LIKE ?",
            (f"{DEMO_PREFIX}:%",),
        )
        return int(access_cursor.rowcount), int(login_cursor.rowcount)


def seed_demo_data(database: Database, *, days: int = 90, seed: int = 7085) -> int:
    """Genera accesos diarios de tres procedencias para el rango solicitado."""
    rng = random.Random(seed)
    today = datetime.now().date()
    total = 0

    for day_offset in range(days - 1, -1, -1):
        event_date = today - timedelta(days=day_offset)
        daily_events = rng.randint(2, 8)

        for event_number in range(daily_events):
            person = rng.choice(PEOPLE)
            first_name, last_name = person
            email_slug = (
                first_name.lower().replace("á", "a")
                + "."
                + last_name.lower().replace("á", "a")
            )
            email = f"{email_slug}.{day_offset:02d}{event_number:02d}@demo.invalid"
            kiosk_index = rng.randint(1, 8)
            kiosk_name = f"{DEMO_PREFIX}: PC-{kiosk_index:02d}"
            client_ip = f"192.0.2.{kiosk_index}"
            event_time = time(
                hour=rng.randint(8, 19),
                minute=rng.choice((0, 10, 15, 20, 30, 40, 45, 50)),
                second=rng.randint(0, 59),
            )
            accessed_at = datetime.combine(event_date, event_time).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            category = rng.random()
            if category < 0.44:
                user_type = "Estudiante Externo"
                university = rng.choice(UNIVERSITIES)
                faculty = ""
                expediente = ""
            elif category < 0.76:
                user_type = "Público en general"
                university = ""
                faculty = ""
                expediente = ""
            else:
                user_type = "Alumno interno"
                university = ""
                faculty = rng.choice(FACULTIES)
                expediente = str(rng.randint(100000, 999999))

            database.record_access_log(
                kiosk_name=kiosk_name,
                nombres=first_name,
                apellidos=last_name,
                expediente=expediente,
                facultad=faculty,
                universidad_externa=university,
                tipo_usuario=user_type,
                accessed_at=accessed_at,
            )

            database.record_received_login(
                kiosk_name=kiosk_name,
                client_ip=client_ip,
                identifier=email,
                user_type=user_type,
                action="unlock_login",
                result="permitido",
                message="Evento de demostración generado por seed_fake_statistics.py",
            )
            total += 1

    return total


def main() -> int:
    database = Database()
    database.initialize()
    removed_accesses, removed_requests = remove_previous_demo_data(database)
    generated = seed_demo_data(database)

    print("Datos de demostración generados correctamente.")
    print(f"Accesos de demostración anteriores eliminados: {removed_accesses}")
    print(f"Logs de peticiones de demostración anteriores eliminados: {removed_requests}")
    print(f"Accesos nuevos generados: {generated}")
    print("Abre DesktopKioskCenter > Estadísticas y selecciona un rango de 90 días.")
    print("Los registros reales no se modificaron.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
