"""Persistencia SQLite de DesktopKioskCenter.

Este módulo concentra el esquema, las migraciones y las consultas de datos.
La interfaz no construye SQL: llama métodos de Database, lo que permite estudiar
y probar las reglas de persistencia sin arrancar PyQt6.

Todas las consultas usan parámetros (?) para no concatenar datos de formularios
en SQL. Cada método abre una conexión corta, confirma la transacción si termina
bien y la revierte ante una excepción.
"""
import json
import logging
import re
import sqlite3
import time
from datetime import date
from contextlib import contextmanager
from pathlib import Path

from const import BASE_DIR, DATABASE_FILE
from user_catalogs import FACULTY_DEFAULTS, INTERNAL_STAFF_TYPES


logger = logging.getLogger(__name__)


class Database:
    """Repositorio SQLite con las operaciones que usa la interfaz.

    Se puede pasar db_path para pruebas automatizadas. En producción se utiliza
    %APPDATA%\\DesktopKioskCenter\\desktopkioskcenter.sqlite3 en Windows.
    """

    def __init__(self, db_path: Path | str | None = None, legacy_dir: Path | str | None = None):
        self.path = Path(db_path) if db_path is not None else DATABASE_FILE
        self.legacy_dir = Path(legacy_dir) if legacy_dir is not None else BASE_DIR

    @contextmanager
    def connection(self):
        """Proporciona una conexión con commit/rollback y cierre garantizado."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(self.path), timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        """Crea las tablas e índices y después importa JSON heredado una sola vez."""
        with self.connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS internal_students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombres TEXT NOT NULL,
                    apellidos TEXT NOT NULL,
                    facultad TEXT NOT NULL,
                    expediente TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                );

                CREATE TABLE IF NOT EXISTS external_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombres TEXT NOT NULL,
                    apellidos TEXT NOT NULL,
                    email TEXT NOT NULL DEFAULT '',
                    tipo_usuario TEXT NOT NULL,
                    universidad TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                );

                CREATE TABLE IF NOT EXISTS internal_staff (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombres TEXT NOT NULL,
                    apellidos TEXT NOT NULL,
                    facultad TEXT NOT NULL,
                    numero_empleado TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL DEFAULT '',
                    tipo_usuario TEXT NOT NULL CHECK (tipo_usuario IN ('Docente', 'Administrativo')),
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                );

                CREATE TABLE IF NOT EXISTS faculties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE
                );

                CREATE TABLE IF NOT EXISTS kiosk_status_codes (
                    status_code INTEGER PRIMARY KEY,
                    label TEXT NOT NULL UNIQUE
                );

                CREATE TABLE IF NOT EXISTS kiosk_heartbeats (
                    client_ip TEXT PRIMARY KEY,
                    kiosk_name TEXT NOT NULL DEFAULT '',
                    status_code INTEGER NOT NULL REFERENCES kiosk_status_codes(status_code),
                    time_string TEXT NOT NULL DEFAULT '00:00:00',
                    last_seen_at REAL NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                );

                CREATE INDEX IF NOT EXISTS idx_kiosk_heartbeats_last_seen
                    ON kiosk_heartbeats(last_seen_at);

                CREATE TABLE IF NOT EXISTS received_logins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    received_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                    kiosk_name TEXT NOT NULL DEFAULT '',
                    client_ip TEXT NOT NULL DEFAULT '',
                    identifier TEXT NOT NULL DEFAULT '',
                    user_type TEXT NOT NULL DEFAULT '',
                    action TEXT NOT NULL DEFAULT 'login',
                    result TEXT NOT NULL DEFAULT '',
                    message TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS access_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    accessed_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                    kiosk_name TEXT NOT NULL DEFAULT '',
                    nombres TEXT NOT NULL DEFAULT '',
                    apellidos TEXT NOT NULL DEFAULT '',
                    expediente TEXT NOT NULL DEFAULT '',
                    facultad TEXT NOT NULL DEFAULT '',
                    universidad_externa TEXT NOT NULL DEFAULT '',
                    tipo_usuario TEXT NOT NULL DEFAULT ''
                );

                CREATE INDEX IF NOT EXISTS idx_access_logs_accessed_at
                    ON access_logs(accessed_at);
                CREATE INDEX IF NOT EXISTS idx_external_users_name
                    ON external_users(apellidos, nombres);
                CREATE INDEX IF NOT EXISTS idx_received_logins_received_at
                    ON received_logins(received_at);
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    migration_key TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                );
                """
            )

            # Catálogo mantenible: los nombres pueden actualizarse en SQLite sin cambiar la UI.
            connection.executemany(
                """INSERT OR IGNORE INTO kiosk_status_codes (status_code, label)
                   VALUES (?, ?)""",
                (
                    (0, "Sin conexión"),
                    (1, "Disponible"),
                    (2, "En uso"),
                    (3, "Inactividad"),
                ),
            )

            faculty_seed_key = "faculty_catalog_defaults_v1"
            faculty_seeded = connection.execute(
                "SELECT 1 FROM schema_migrations WHERE migration_key = ?",
                (faculty_seed_key,),
            ).fetchone()
            if not faculty_seeded:
                connection.executemany(
                    "INSERT OR IGNORE INTO faculties (name) VALUES (?)",
                    ((faculty,) for faculty in FACULTY_DEFAULTS),
                )
                connection.execute(
                    "INSERT INTO schema_migrations (migration_key) VALUES (?)",
                    (faculty_seed_key,),
                )

            # Migraciones incrementales de correo electrónico en las categorías de usuarios.
            internal_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(internal_students)")
            }
            if "email" not in internal_columns:
                connection.execute(
                    "ALTER TABLE internal_students ADD COLUMN email TEXT NOT NULL DEFAULT ''"
                )

            staff_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(internal_staff)")
            }
            if "email" not in staff_columns:
                connection.execute(
                    "ALTER TABLE internal_staff ADD COLUMN email TEXT NOT NULL DEFAULT ''"
                )

            external_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(external_users)")
            }
            if "email" not in external_columns:
                connection.execute(
                    "ALTER TABLE external_users ADD COLUMN email TEXT NOT NULL DEFAULT ''"
                )

            connection.execute(
                """CREATE UNIQUE INDEX IF NOT EXISTS idx_internal_students_email_unique
                   ON internal_students(email COLLATE NOCASE)
                   WHERE TRIM(email) <> ''"""
            )
            connection.execute(
                """CREATE UNIQUE INDEX IF NOT EXISTS idx_internal_staff_email_unique
                   ON internal_staff(email COLLATE NOCASE)
                   WHERE TRIM(email) <> ''"""
            )
            connection.execute(
                """CREATE UNIQUE INDEX IF NOT EXISTS idx_external_users_email_unique
                   ON external_users(email COLLATE NOCASE)
                   WHERE TRIM(email) <> ''"""
            )

            # Garantiza unicidad del correo entre tablas, no solo dentro de cada tipo.
            connection.executescript(
                """
                CREATE TRIGGER IF NOT EXISTS trg_internal_email_not_in_external_insert
                BEFORE INSERT ON internal_students
                WHEN TRIM(NEW.email) <> ''
                BEGIN
                    SELECT RAISE(ABORT, 'email already registered')
                    WHERE EXISTS (
                        SELECT 1 FROM external_users
                        WHERE TRIM(email) <> '' AND email = NEW.email COLLATE NOCASE
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS trg_internal_email_not_in_external_update
                BEFORE UPDATE OF email ON internal_students
                WHEN TRIM(NEW.email) <> ''
                BEGIN
                    SELECT RAISE(ABORT, 'email already registered')
                    WHERE EXISTS (
                        SELECT 1 FROM external_users
                        WHERE TRIM(email) <> '' AND email = NEW.email COLLATE NOCASE
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS trg_external_email_not_in_internal_insert
                BEFORE INSERT ON external_users
                WHEN TRIM(NEW.email) <> ''
                BEGIN
                    SELECT RAISE(ABORT, 'email already registered')
                    WHERE EXISTS (
                        SELECT 1 FROM internal_students
                        WHERE TRIM(email) <> '' AND email = NEW.email COLLATE NOCASE
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS trg_external_email_not_in_internal_update
                BEFORE UPDATE OF email ON external_users
                WHEN TRIM(NEW.email) <> ''
                BEGIN
                    SELECT RAISE(ABORT, 'email already registered')
                    WHERE EXISTS (
                        SELECT 1 FROM internal_students
                        WHERE TRIM(email) <> '' AND email = NEW.email COLLATE NOCASE
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS trg_staff_email_not_in_students_insert
                BEFORE INSERT ON internal_staff
                WHEN TRIM(NEW.email) <> ''
                BEGIN
                    SELECT RAISE(ABORT, 'email already registered')
                    WHERE EXISTS (
                        SELECT 1 FROM internal_students
                        WHERE TRIM(email) <> '' AND email = NEW.email COLLATE NOCASE
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS trg_staff_email_not_in_students_update
                BEFORE UPDATE OF email ON internal_staff
                WHEN TRIM(NEW.email) <> ''
                BEGIN
                    SELECT RAISE(ABORT, 'email already registered')
                    WHERE EXISTS (
                        SELECT 1 FROM internal_students
                        WHERE TRIM(email) <> '' AND email = NEW.email COLLATE NOCASE
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS trg_staff_email_not_in_external_insert
                BEFORE INSERT ON internal_staff
                WHEN TRIM(NEW.email) <> ''
                BEGIN
                    SELECT RAISE(ABORT, 'email already registered')
                    WHERE EXISTS (
                        SELECT 1 FROM external_users
                        WHERE TRIM(email) <> '' AND email = NEW.email COLLATE NOCASE
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS trg_staff_email_not_in_external_update
                BEFORE UPDATE OF email ON internal_staff
                WHEN TRIM(NEW.email) <> ''
                BEGIN
                    SELECT RAISE(ABORT, 'email already registered')
                    WHERE EXISTS (
                        SELECT 1 FROM external_users
                        WHERE TRIM(email) <> '' AND email = NEW.email COLLATE NOCASE
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS trg_students_email_not_in_staff_insert
                BEFORE INSERT ON internal_students
                WHEN TRIM(NEW.email) <> ''
                BEGIN
                    SELECT RAISE(ABORT, 'email already registered')
                    WHERE EXISTS (
                        SELECT 1 FROM internal_staff
                        WHERE TRIM(email) <> '' AND email = NEW.email COLLATE NOCASE
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS trg_students_email_not_in_staff_update
                BEFORE UPDATE OF email ON internal_students
                WHEN TRIM(NEW.email) <> ''
                BEGIN
                    SELECT RAISE(ABORT, 'email already registered')
                    WHERE EXISTS (
                        SELECT 1 FROM internal_staff
                        WHERE TRIM(email) <> '' AND email = NEW.email COLLATE NOCASE
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS trg_external_email_not_in_staff_insert
                BEFORE INSERT ON external_users
                WHEN TRIM(NEW.email) <> ''
                BEGIN
                    SELECT RAISE(ABORT, 'email already registered')
                    WHERE EXISTS (
                        SELECT 1 FROM internal_staff
                        WHERE TRIM(email) <> '' AND email = NEW.email COLLATE NOCASE
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS trg_external_email_not_in_staff_update
                BEFORE UPDATE OF email ON external_users
                WHEN TRIM(NEW.email) <> ''
                BEGIN
                    SELECT RAISE(ABORT, 'email already registered')
                    WHERE EXISTS (
                        SELECT 1 FROM internal_staff
                        WHERE TRIM(email) <> '' AND email = NEW.email COLLATE NOCASE
                    );
                END;
                """
            )

        self._migrate_legacy_json()
        self._sync_faculty_catalog_from_records()

    def _sync_faculty_catalog_from_records(self) -> None:
        """Importa una sola vez las facultades de datos previos a este catálogo."""
        migration_key = "faculty_catalog_existing_data_v1"
        with self.connection() as connection:
            already_applied = connection.execute(
                "SELECT 1 FROM schema_migrations WHERE migration_key = ?",
                (migration_key,),
            ).fetchone()
            if already_applied:
                return

            connection.execute(
                """
                INSERT OR IGNORE INTO faculties (name)
                SELECT name
                FROM (
                    SELECT TRIM(facultad) AS name
                    FROM internal_students
                    WHERE TRIM(facultad) <> ''
                    UNION
                    SELECT TRIM(facultad) AS name
                    FROM internal_staff
                    WHERE TRIM(facultad) <> ''
                    UNION
                    SELECT TRIM(facultad) AS name
                    FROM access_logs
                    WHERE TRIM(facultad) <> ''
                )
                WHERE TRIM(name) <> ''
                """
            )
            connection.execute(
                "INSERT INTO schema_migrations (migration_key) VALUES (?)",
                (migration_key,),
            )

    def _migrate_legacy_json(self) -> None:
        """Importa los JSON usados por versiones anteriores sin eliminarlos.

        El marcador schema_migrations impide duplicar los datos en cada arranque.
        Los JSON originales se conservan como respaldo. Las filas inválidas se
        registran en el log y se omiten; los expedientes duplicados no se vuelven
        a insertar porque expediente es único.
        """
        migration_key = "legacy_user_json_to_sqlite_v1"
        with self.connection() as connection:
            already_applied = connection.execute(
                "SELECT 1 FROM schema_migrations WHERE migration_key = ?",
                (migration_key,),
            ).fetchone()
            if already_applied:
                return

            migration_ok = True
            migration_specs = (
                (
                    "internal_students.json",
                    """
                    INSERT OR IGNORE INTO internal_students
                        (nombres, apellidos, facultad, expediente)
                    VALUES (?, ?, ?, ?)
                    """,
                    ("nombres", "apellidos", "facultad", "expediente"),
                ),
                (
                    "external_users.json",
                    """
                    INSERT INTO external_users
                        (nombres, apellidos, tipo_usuario, universidad)
                    VALUES (?, ?, ?, ?)
                    """,
                    ("nombres", "apellidos", "tipo_usuario", "universidad"),
                ),
            )

            for filename, sql, fields in migration_specs:
                legacy_file = self.legacy_dir / filename
                if not legacy_file.exists():
                    continue

                try:
                    payload = json.loads(legacy_file.read_text(encoding="utf-8"))
                    if not isinstance(payload, list):
                        raise ValueError("El archivo debe contener una lista JSON.")
                except (OSError, ValueError) as exc:
                    logger.warning("No se pudo migrar %s: %s", legacy_file, exc)
                    migration_ok = False
                    continue

                for row_number, item in enumerate(payload, start=1):
                    if not isinstance(item, dict):
                        logger.warning(
                            "Se omitió la fila %s de %s: no es un objeto JSON.",
                            row_number,
                            legacy_file,
                        )
                        continue

                    values = tuple(str(item.get(field, "") or "").strip() for field in fields)
                    if any(not value for value in values):
                        logger.warning(
                            "Se omitió la fila %s de %s: faltan datos obligatorios.",
                            row_number,
                            legacy_file,
                        )
                        continue

                    try:
                        connection.execute(sql, values)
                    except sqlite3.IntegrityError as exc:
                        # Por ejemplo, un expediente que ya existe en SQLite.
                        logger.warning(
                            "Se omitió la fila %s de %s por integridad: %s",
                            row_number,
                            legacy_file,
                            exc,
                        )

            if migration_ok:
                connection.execute(
                    "INSERT OR IGNORE INTO schema_migrations (migration_key) VALUES (?)",
                    (migration_key,),
                )

    @staticmethod
    def _as_dicts(rows):
        return [dict(row) for row in rows]

    def list_kiosk_status_codes(self) -> list[dict]:
        """Devuelve el catálogo de estados, ordenado por código."""
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT status_code, label FROM kiosk_status_codes ORDER BY status_code"
            ).fetchall()
            return self._as_dicts(rows)

    def get_kiosk_status_label(self, status_code: int) -> str:
        """Resuelve una etiqueta desde el catálogo mantenido en SQLite."""
        with self.connection() as connection:
            row = connection.execute(
                "SELECT label FROM kiosk_status_codes WHERE status_code = ?",
                (int(status_code),),
            ).fetchone()
            return str(row["label"]) if row else str(status_code)

    def update_kiosk_status_label(self, status_code: int, label: str) -> bool:
        """Actualiza una etiqueta del catálogo sin cambiar el código de estado."""
        normalized_label = str(label or "").strip()
        if not normalized_label:
            raise ValueError("La etiqueta del estado no puede estar vacía.")
        with self.connection() as connection:
            cursor = connection.execute(
                "UPDATE kiosk_status_codes SET label = ? WHERE status_code = ?",
                (normalized_label, int(status_code)),
            )
            return cursor.rowcount > 0

    def record_kiosk_heartbeat(
        self,
        *,
        client_ip: str,
        status_code: int,
        time_string: str,
        kiosk_name: str = "",
        last_seen_at: float | None = None,
    ) -> None:
        """Inserta o actualiza el heartbeat más reciente recibido para una IP."""
        if isinstance(status_code, bool) or int(status_code) not in (1, 2, 3):
            raise ValueError("El estado de heartbeat debe ser 1, 2 o 3.")
        client_ip = str(client_ip or "").strip()
        if not client_ip:
            raise ValueError("La IP de origen es obligatoria.")
        time_string = str(time_string or "").strip()
        if not time_string:
            raise ValueError("time_string es obligatorio.")
        observed_at = time.time() if last_seen_at is None else float(last_seen_at)

        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO kiosk_heartbeats
                    (client_ip, kiosk_name, status_code, time_string, last_seen_at, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
                ON CONFLICT(client_ip) DO UPDATE SET
                    kiosk_name = excluded.kiosk_name,
                    status_code = excluded.status_code,
                    time_string = excluded.time_string,
                    last_seen_at = excluded.last_seen_at,
                    updated_at = datetime('now', 'localtime')
                """,
                (client_ip, str(kiosk_name or "").strip()[:200], int(status_code), time_string, observed_at),
            )

    def mark_stale_kiosks_offline(
        self, timeout_seconds: float = 4.0, *, now: float | None = None
    ) -> int:
        """Pasa a estado 0 los clientes cuyo último heartbeat venció."""
        current_time = time.time() if now is None else float(now)
        cutoff = current_time - max(0.0, float(timeout_seconds))
        with self.connection() as connection:
            cursor = connection.execute(
                """
                UPDATE kiosk_heartbeats
                SET status_code = 0, updated_at = datetime('now', 'localtime')
                WHERE last_seen_at <= ? AND status_code <> 0
                """,
                (cutoff,),
            )
            return int(cursor.rowcount)

    def list_kiosk_heartbeats(self) -> list[dict]:
        """Devuelve el último estado recibido de cada IP con la etiqueta del catálogo."""
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT h.client_ip, h.kiosk_name, h.status_code,
                       s.label AS status_label, h.time_string, h.last_seen_at, h.updated_at
                FROM kiosk_heartbeats AS h
                JOIN kiosk_status_codes AS s ON s.status_code = h.status_code
                ORDER BY h.client_ip
                """
            ).fetchall()
            return self._as_dicts(rows)

    def get_kiosk_heartbeat(self, client_ip: str) -> dict | None:
        """Obtiene el estado registrado para una IP o None si nunca hubo heartbeat."""
        with self.connection() as connection:
            row = connection.execute(
                """
                SELECT h.client_ip, h.kiosk_name, h.status_code,
                       s.label AS status_label, h.time_string, h.last_seen_at, h.updated_at
                FROM kiosk_heartbeats AS h
                JOIN kiosk_status_codes AS s ON s.status_code = h.status_code
                WHERE h.client_ip = ?
                """,
                (str(client_ip or "").strip(),),
            ).fetchone()
            return dict(row) if row else None

    def delete_kiosk_heartbeats(self, client_ips: list[str]) -> int:
        """Elimina los heartbeats de los equipos retirados de la configuración."""
        normalized_ips = sorted({
            str(client_ip or "").strip()
            for client_ip in client_ips
            if str(client_ip or "").strip()
        })
        if not normalized_ips:
            return 0
        placeholders = ", ".join("?" for _ in normalized_ips)
        with self.connection() as connection:
            cursor = connection.execute(
                f"DELETE FROM kiosk_heartbeats WHERE client_ip IN ({placeholders})",
                normalized_ips,
            )
            return int(cursor.rowcount)

    def list_faculties(self) -> list[str]:
        """Devuelve el catálogo compartido de facultades en orden alfabético."""
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT name FROM faculties ORDER BY name COLLATE NOCASE"
            ).fetchall()
            return [str(row["name"]) for row in rows]

    def add_faculty(self, name: str) -> bool:
        """Agrega una facultad al catálogo común."""
        normalized = str(name or "").strip()
        if not normalized:
            raise ValueError("El nombre de la facultad no puede estar vacío.")
        with self.connection() as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO faculties (name) VALUES (?)",
                (normalized,),
            )
            return cursor.rowcount > 0

    def rename_faculty(self, old_name: str, new_name: str) -> bool:
        """Renombra una facultad y actualiza sus registros e historial asociado."""
        old_value = str(old_name or "").strip()
        new_value = str(new_name or "").strip()
        if not old_value or not new_value:
            raise ValueError("Los nombres de facultad no pueden estar vacíos.")
        if old_value.casefold() == new_value.casefold():
            return False
        with self.connection() as connection:
            if connection.execute(
                "SELECT 1 FROM faculties WHERE name = ? COLLATE NOCASE",
                (new_value,),
            ).fetchone():
                raise sqlite3.IntegrityError("faculty already exists")
            cursor = connection.execute(
                "UPDATE faculties SET name = ? WHERE name = ? COLLATE NOCASE",
                (new_value, old_value),
            )
            if not cursor.rowcount:
                return False
            connection.execute(
                "UPDATE internal_students SET facultad = ? WHERE facultad = ? COLLATE NOCASE",
                (new_value, old_value),
            )
            connection.execute(
                "UPDATE internal_staff SET facultad = ? WHERE facultad = ? COLLATE NOCASE",
                (new_value, old_value),
            )
            connection.execute(
                "UPDATE access_logs SET facultad = ? WHERE facultad = ? COLLATE NOCASE",
                (new_value, old_value),
            )
            return True

    def delete_faculty(self, name: str) -> bool:
        """Elimina una facultad solo si ningún usuario registrado la utiliza."""
        normalized = str(name or "").strip()
        if not normalized:
            return False
        with self.connection() as connection:
            used = connection.execute(
                """
                SELECT 1 FROM internal_students WHERE facultad = ? COLLATE NOCASE
                UNION ALL
                SELECT 1 FROM internal_staff WHERE facultad = ? COLLATE NOCASE
                LIMIT 1
                """,
                (normalized, normalized),
            ).fetchone()
            if used:
                raise ValueError(
                    "No se puede eliminar esta facultad porque está asignada a usuarios registrados. "
                    "Reasigna primero esos registros."
                )
            cursor = connection.execute(
                "DELETE FROM faculties WHERE name = ? COLLATE NOCASE",
                (normalized,),
            )
            return cursor.rowcount > 0

    def list_internal_students(self) -> list[dict]:
        """Devuelve los alumnos internos en orden de alta."""
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT id, nombres, apellidos, facultad, expediente, email, created_at
                FROM internal_students
                ORDER BY id
                """
            ).fetchall()
            return self._as_dicts(rows)

    def add_internal_student(self, record: dict) -> int:
        """Inserta un alumno con email único en el catálogo completo de usuarios."""
        email = self._validate_email(record.get("email", ""))
        with self.connection() as connection:
            if self._email_in_use(connection, email):
                raise sqlite3.IntegrityError("email already registered")
            expediente = str(record.get("expediente", "") or "").strip()
            if not expediente or self._internal_identifier_in_use(connection, expediente):
                raise sqlite3.IntegrityError("internal identifier already registered")
            cursor = connection.execute(
                """
                INSERT INTO internal_students
                    (nombres, apellidos, facultad, expediente, email)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    record["nombres"].strip(),
                    record["apellidos"].strip(),
                    record["facultad"].strip(),
                    record["expediente"].strip(),
                    email,
                ),
            )
            return int(cursor.lastrowid)

    def update_internal_student(self, student_id: int, record: dict) -> bool:
        """Actualiza un alumno y garantiza la unicidad de email."""
        email = self._validate_email(record.get("email", ""))
        with self.connection() as connection:
            if self._email_in_use(
                connection, email, exclude_internal_student_id=int(student_id)
            ):
                raise sqlite3.IntegrityError("email already registered")
            expediente = str(record.get("expediente", "") or "").strip()
            if not expediente or self._internal_identifier_in_use(
                connection, expediente, exclude_student_id=int(student_id)
            ):
                raise sqlite3.IntegrityError("internal identifier already registered")
            cursor = connection.execute(
                """UPDATE internal_students
                   SET nombres = ?, apellidos = ?, facultad = ?, expediente = ?, email = ?
                   WHERE id = ?""",
                (record["nombres"].strip(), record["apellidos"].strip(),
                 record["facultad"].strip(), record["expediente"].strip(),
                 email, int(student_id)),
            )
            return cursor.rowcount > 0

    def delete_internal_student(self, student_id: int) -> bool:
        """Elimina el alumno por su clave primaria SQLite."""
        with self.connection() as connection:
            cursor = connection.execute(
                "DELETE FROM internal_students WHERE id = ?", (int(student_id),)
            )
            return cursor.rowcount > 0

    def list_internal_staff(self) -> list[dict]:
        """Lista docentes y administrativos; expediente se expone como alias de auditoría."""
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT id, nombres, apellidos, email, facultad, numero_empleado,
                       numero_empleado AS expediente, tipo_usuario, created_at
                FROM internal_staff
                ORDER BY tipo_usuario, apellidos COLLATE NOCASE, nombres COLLATE NOCASE
                """
            ).fetchall()
            return self._as_dicts(rows)

    def add_internal_staff(self, record: dict) -> int:
        """Registra un docente o administrativo con correo y número de empleado únicos."""
        email = self._validate_email(record.get("email", ""))
        employee_number = str(record.get("numero_empleado", "") or "").strip()
        user_type = str(record.get("tipo_usuario", "") or "").strip()
        if user_type not in INTERNAL_STAFF_TYPES:
            raise ValueError("El tipo de personal debe ser Docente o Administrativo.")
        if not employee_number.isdigit():
            raise ValueError("El número de empleado debe contener únicamente números.")
        with self.connection() as connection:
            if self._email_in_use(connection, email):
                raise sqlite3.IntegrityError("email already registered")
            if self._internal_identifier_in_use(connection, employee_number):
                raise sqlite3.IntegrityError("internal identifier already registered")
            cursor = connection.execute(
                """
                INSERT INTO internal_staff
                    (nombres, apellidos, email, tipo_usuario, facultad, numero_empleado)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(record.get("nombres", "")).strip(),
                    str(record.get("apellidos", "")).strip(),
                    email,
                    user_type,
                    str(record.get("facultad", "")).strip(),
                    employee_number,
                ),
            )
            return int(cursor.lastrowid)

    def update_internal_staff(self, staff_id: int, record: dict) -> bool:
        """Actualiza un registro de personal y conserva unicidad global."""
        email = self._validate_email(record.get("email", ""))
        employee_number = str(record.get("numero_empleado", "") or "").strip()
        user_type = str(record.get("tipo_usuario", "") or "").strip()
        if user_type not in INTERNAL_STAFF_TYPES:
            raise ValueError("El tipo de personal debe ser Docente o Administrativo.")
        if not employee_number.isdigit():
            raise ValueError("El número de empleado debe contener únicamente números.")
        with self.connection() as connection:
            if self._email_in_use(
                connection, email, exclude_internal_staff_id=int(staff_id)
            ):
                raise sqlite3.IntegrityError("email already registered")
            if self._internal_identifier_in_use(
                connection, employee_number, exclude_staff_id=int(staff_id)
            ):
                raise sqlite3.IntegrityError("internal identifier already registered")
            cursor = connection.execute(
                """
                UPDATE internal_staff
                SET nombres = ?, apellidos = ?, email = ?, tipo_usuario = ?,
                    facultad = ?, numero_empleado = ?
                WHERE id = ?
                """,
                (
                    str(record.get("nombres", "")).strip(),
                    str(record.get("apellidos", "")).strip(),
                    email,
                    user_type,
                    str(record.get("facultad", "")).strip(),
                    employee_number,
                    int(staff_id),
                ),
            )
            return cursor.rowcount > 0

    def delete_internal_staff(self, staff_id: int) -> bool:
        """Elimina el registro de personal seleccionado."""
        with self.connection() as connection:
            cursor = connection.execute(
                "DELETE FROM internal_staff WHERE id = ?", (int(staff_id),)
            )
            return cursor.rowcount > 0

    def list_external_users(self) -> list[dict]:
        """Devuelve los usuarios externos y público general en orden de alta."""
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT id, nombres, apellidos, email, tipo_usuario, universidad, created_at
                FROM external_users
                ORDER BY id
                """
            ).fetchall()
            return self._as_dicts(rows)

    @staticmethod
    def _validate_email(email) -> str:
        """Valida el correo electrónico común a todos los usuarios registrados."""
        email = str(email or "").strip()
        if not email:
            raise ValueError("El correo electrónico es obligatorio.")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("La dirección de correo electrónico no es válida.")
        return email

    @staticmethod
    def _validate_external_email(email) -> str:
        """Valida el correo obligatorio de los usuarios externos."""
        email = str(email or "").strip()
        if not email:
            raise ValueError("El email es obligatorio para todos los usuarios externos.")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("La dirección de email no es válida.")
        return email

    @staticmethod
    def _email_in_use(
        connection,
        email: str,
        *,
        exclude_internal_student_id: int | None = None,
        exclude_internal_staff_id: int | None = None,
        exclude_external_user_id: int | None = None,
    ) -> bool:
        for table, excluded_id in (
            ("internal_students", exclude_internal_student_id),
            ("internal_staff", exclude_internal_staff_id),
            ("external_users", exclude_external_user_id),
        ):
            sql = (
                f"SELECT 1 FROM {table} "
                "WHERE TRIM(email) <> '' AND email = ? COLLATE NOCASE"
            )
            params: tuple = (email,)
            if excluded_id is not None:
                sql += " AND id <> ?"
                params += (int(excluded_id),)
            if connection.execute(sql + " LIMIT 1", params).fetchone():
                return True
        return False

    @staticmethod
    def _internal_identifier_in_use(
        connection,
        identifier: str,
        *,
        exclude_student_id: int | None = None,
        exclude_staff_id: int | None = None,
    ) -> bool:
        student_sql = "SELECT 1 FROM internal_students WHERE expediente = ?"
        student_params: tuple = (identifier,)
        if exclude_student_id is not None:
            student_sql += " AND id <> ?"
            student_params += (int(exclude_student_id),)
        if connection.execute(student_sql + " LIMIT 1", student_params).fetchone():
            return True

        staff_sql = "SELECT 1 FROM internal_staff WHERE numero_empleado = ?"
        staff_params: tuple = (identifier,)
        if exclude_staff_id is not None:
            staff_sql += " AND id <> ?"
            staff_params += (int(exclude_staff_id),)
        return connection.execute(staff_sql + " LIMIT 1", staff_params).fetchone() is not None

        """Valida que todo usuario externo tenga un email válido."""
        email = str(email or "").strip()
        if not email:
            raise ValueError("El email es obligatorio para todos los usuarios externos.")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("La dirección de email no es válida.")
        return email

    def add_external_user(self, record: dict) -> int:
        """Inserta un usuario externo con email obligatorio."""
        email = self._validate_external_email(record.get("email", ""))
        tipo_usuario = record["tipo_usuario"].strip()
        universidad = record.get("universidad", "").strip()
        if tipo_usuario != "Estudiante Externo":
            # Solo un estudiante externo debe quedar vinculado a una universidad.
            universidad = ""

        with self.connection() as connection:
            if self._email_in_use(connection, email):
                raise sqlite3.IntegrityError("email already registered")
            cursor = connection.execute(
                """
                INSERT INTO external_users
                    (nombres, apellidos, email, tipo_usuario, universidad)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    record["nombres"].strip(),
                    record["apellidos"].strip(),
                    email,
                    tipo_usuario,
                    universidad,
                ),
            )
            return int(cursor.lastrowid)

    def update_external_user(self, user_id: int, record: dict) -> bool:
        """Actualiza un usuario con email válido; limpia universidad si no aplica."""
        email = self._validate_external_email(record.get("email", ""))
        tipo_usuario = record["tipo_usuario"].strip()
        universidad = record.get("universidad", "").strip()
        if tipo_usuario != "Estudiante Externo":
            universidad = ""
        with self.connection() as connection:
            if self._email_in_use(connection, email, exclude_external_user_id=int(user_id)):
                raise sqlite3.IntegrityError("email already registered")
            cursor = connection.execute(
                """UPDATE external_users
                   SET nombres = ?, apellidos = ?, email = ?, tipo_usuario = ?, universidad = ?
                   WHERE id = ?""",
                (record["nombres"].strip(), record["apellidos"].strip(),
                 email, tipo_usuario, universidad, int(user_id)),
            )
            return cursor.rowcount > 0

    def delete_external_user(self, user_id: int) -> bool:
        """Elimina el usuario por su clave primaria SQLite."""
        with self.connection() as connection:
            cursor = connection.execute(
                "DELETE FROM external_users WHERE id = ?", (int(user_id),)
            )
            return cursor.rowcount > 0

    def find_registered_user(self, identifier: str) -> dict | None:
        """Busca por email y por identificador institucional de usuarios internos."""
        identifier = str(identifier or "").strip()
        if not identifier:
            return None
        with self.connection() as connection:
            student_by_email = connection.execute(
                """SELECT id, nombres, apellidos, facultad, expediente,
                          email, '' AS universidad, 'Alumno interno' AS tipo_usuario
                   FROM internal_students
                   WHERE email <> '' AND email = ? COLLATE NOCASE""",
                (identifier,),
            ).fetchone()
            if student_by_email:
                return dict(student_by_email)

            staff_by_email = connection.execute(
                """SELECT id, nombres, apellidos, facultad,
                          numero_empleado AS expediente, numero_empleado,
                          email, '' AS universidad, tipo_usuario
                   FROM internal_staff
                   WHERE email <> '' AND email = ? COLLATE NOCASE""",
                (identifier,),
            ).fetchone()
            if staff_by_email:
                return dict(staff_by_email)

            external = connection.execute(
                """SELECT id, nombres, apellidos, '' AS facultad, '' AS expediente,
                          email, universidad, tipo_usuario
                   FROM external_users
                   WHERE email <> '' AND email = ? COLLATE NOCASE""",
                (identifier,),
            ).fetchone()
            if external:
                return dict(external)

            staff_by_number = connection.execute(
                """SELECT id, nombres, apellidos, facultad,
                          numero_empleado AS expediente, numero_empleado,
                          email, '' AS universidad, tipo_usuario
                   FROM internal_staff WHERE numero_empleado = ?""",
                (identifier,),
            ).fetchone()
            if staff_by_number:
                return dict(staff_by_number)

            student_by_expediente = connection.execute(
                """SELECT id, nombres, apellidos, facultad, expediente,
                          email, '' AS universidad, 'Alumno interno' AS tipo_usuario
                   FROM internal_students WHERE expediente = ?""",
                (identifier,),
            ).fetchone()
            return dict(student_by_expediente) if student_by_expediente else None

    def external_user_exists(self, record: dict) -> bool:
        """Comprueba si el correo ya existe en cualquier categoría de usuario."""
        email = self._validate_external_email(record.get("email", ""))
        with self.connection() as connection:
            return self._email_in_use(connection, email)

    def email_exists(self, email: str) -> bool:
        """Comprueba la unicidad global del correo electrónico."""
        email = self._validate_email(email)
        with self.connection() as connection:
            return self._email_in_use(connection, email)

    def list_access_logs(self, limit: int | None = 1000) -> list[dict]:
        """Lista los eventos de acceso más recientes."""
        fields = ("id, accessed_at, kiosk_name, nombres, apellidos, expediente, "
                  "facultad, universidad_externa, tipo_usuario")
        with self.connection() as connection:
            if limit is None:
                rows = connection.execute(
                    f"SELECT {fields} FROM access_logs ORDER BY id DESC"
                ).fetchall()
            else:
                rows = connection.execute(
                    f"SELECT {fields} FROM access_logs ORDER BY id DESC LIMIT ?",
                    (max(1, int(limit)),),
                ).fetchall()
            return self._as_dicts(rows)

    def record_access_log(
        self, *, kiosk_name: str = "", nombres: str = "", apellidos: str = "",
        expediente: str = "", facultad: str = "", universidad_externa: str = "",
        tipo_usuario: str = "", accessed_at: str | None = None,
    ) -> int:
        """Registra un acceso para que lo invoque el servicio de autenticación."""
        values = (kiosk_name.strip(), nombres.strip(), apellidos.strip(),
                  expediente.strip(), facultad.strip(), universidad_externa.strip(),
                  tipo_usuario.strip())
        with self.connection() as connection:
            if accessed_at:
                cursor = connection.execute(
                    """INSERT INTO access_logs
                       (accessed_at, kiosk_name, nombres, apellidos, expediente,
                        facultad, universidad_externa, tipo_usuario)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (accessed_at.strip(), *values),
                )
            else:
                cursor = connection.execute(
                    """INSERT INTO access_logs
                       (kiosk_name, nombres, apellidos, expediente, facultad,
                        universidad_externa, tipo_usuario)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    values,
                )
            return int(cursor.lastrowid)

    def record_manual_user_session(
        self, *, kiosk_name: str, client_ip: str, user: dict
    ) -> dict:
        """Registra una sesión asignada desde el panel administrativo.

        La asignación se marca como simulación en received_logins para distinguirla
        del registro/inicio de sesión hecho directamente en el kiosco. El acceso
        queda atribuido al usuario real seleccionado y las tres filas se guardan
        en una sola transacción.
        """
        user_type = str(user.get("tipo_usuario") or "Alumno interno").strip()
        if user_type not in (
            "Alumno interno", "Docente", "Administrativo", "Público en general"
        ):
            raise ValueError(
                "La asignación remota solo admite alumnos, docentes, administrativos "
                "y público en general."
            )

        identifier = str(
            user.get("numero_empleado") or user.get("email") or user.get("expediente") or ""
        ).strip()
        if not identifier:
            raise ValueError(
                "El usuario debe tener correo, expediente o número de empleado "
                "para auditar la sesión."
            )

        equipment = str(kiosk_name or "").strip()
        source_ip = str(client_ip or "").strip()
        names = str(user.get("nombres", "") or "").strip()
        surnames = str(user.get("apellidos", "") or "").strip()
        faculty = str(user.get("facultad", "") or "").strip()
        university = (
            str(user.get("universidad", "") or "").strip()
            if user_type == "Estudiante Externo" else ""
        )
        if user_type == "Público en general":
            registration_action = "registro_usuario_simulado"
        elif user_type in ("Docente", "Administrativo"):
            registration_action = "registro_personal_simulado"
        else:
            registration_action = "registro_alumno_simulado"

        with self.connection() as connection:
            registration = connection.execute(
                """
                INSERT INTO received_logins
                    (kiosk_name, client_ip, identifier, user_type, action, result, message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    equipment, source_ip, identifier, user_type,
                    registration_action, "registrado (simulación administrativa)",
                    "Registro atribuido al usuario durante una asignación administrativa.",
                ),
            )
            unlock = connection.execute(
                """
                INSERT INTO received_logins
                    (kiosk_name, client_ip, identifier, user_type, action, result, message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    equipment, source_ip, identifier, user_type,
                    "unlock_login_simulado", "permitido (simulación administrativa)",
                    "El kiosco confirmó el inicio de sesión atribuido al usuario seleccionado.",
                ),
            )
            access = connection.execute(
                """
                INSERT INTO access_logs
                    (kiosk_name, nombres, apellidos, expediente, facultad,
                     universidad_externa, tipo_usuario)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    equipment, names, surnames,
                    str(
                        user.get("numero_empleado") or user.get("expediente") or ""
                    ).strip(),
                    faculty, university, user_type,
                ),
            )
            return {
                "registration_log_id": int(registration.lastrowid),
                "unlock_log_id": int(unlock.lastrowid),
                "access_log_id": int(access.lastrowid),
            }

    def record_manual_student_unlock(
        self, *, kiosk_name: str, client_ip: str, student: dict
    ) -> dict:
        """Compatibilidad con las pruebas y llamadas de asignación de alumno."""
        return self.record_manual_user_session(
            kiosk_name=kiosk_name,
            client_ip=client_ip,
            user={**student, "tipo_usuario": "Alumno interno"},
        )

    def count_access_logs(self) -> dict:
        """Calcula total de accesos y subtotales por tipo de usuario y equipo."""
        with self.connection() as connection:
            total = connection.execute("SELECT COUNT(*) FROM access_logs").fetchone()[0]
            by_type = connection.execute(
                """SELECT COALESCE(NULLIF(tipo_usuario, ''), 'Sin especificar') AS label,
                          COUNT(*) AS total
                   FROM access_logs GROUP BY label ORDER BY total DESC, label"""
            ).fetchall()
            by_kiosk = connection.execute(
                """SELECT COALESCE(NULLIF(kiosk_name, ''), 'Sin especificar') AS label,
                          COUNT(*) AS total
                   FROM access_logs GROUP BY label ORDER BY total DESC, label"""
            ).fetchall()
            return {"total": int(total), "by_type": self._as_dicts(by_type),
                    "by_kiosk": self._as_dicts(by_kiosk)}

    def generate_access_report(
        self, start_date: str, end_date: str, grouping: str = "day"
    ) -> list[dict]:
        """Agrupa accesos por día, semana (lunes) o mes y por procedencia."""
        try:
            start = date.fromisoformat(str(start_date))
            end = date.fromisoformat(str(end_date))
        except (TypeError, ValueError) as exc:
            raise ValueError("Las fechas deben tener formato AAAA-MM-DD.") from exc
        if end < start:
            raise ValueError("La fecha final no puede ser anterior a la fecha inicial.")

        period_expressions = {
            "day": "date(accessed_at)",
            "week": (
                "date(accessed_at, '-' || "
                "((CAST(strftime('%w', accessed_at) AS INTEGER) + 6) % 7) || ' days')"
            ),
            "month": "strftime('%Y-%m', accessed_at)",
        }
        if grouping not in period_expressions:
            raise ValueError("La agrupación debe ser day, week o month.")

        period_expression = period_expressions[grouping]
        with self.connection() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    {period_expression} AS period,
                    CASE
                        WHEN lower(trim(tipo_usuario)) IN ('estudiante externo', 'estudiante')
                            THEN 'Universidad'
                        WHEN lower(trim(tipo_usuario)) IN
                             ('público en general', 'publico en general', 'publico_general')
                            THEN 'Público en general'
                        WHEN lower(trim(tipo_usuario)) IN ('alumno interno', 'trabajador interno', 'docente', 'administrativo')
                            THEN 'UAQ'
                        ELSE COALESCE(NULLIF(trim(tipo_usuario), ''), 'Sin clasificar')
                    END AS origin,
                    CASE
                        WHEN lower(trim(tipo_usuario)) IN ('estudiante externo', 'estudiante')
                            THEN COALESCE(NULLIF(trim(universidad_externa), ''),
                                          'Universidad no especificada')
                        WHEN lower(trim(tipo_usuario)) IN
                             ('público en general', 'publico en general', 'publico_general')
                            THEN 'Público en general'
                        WHEN lower(trim(tipo_usuario)) IN ('alumno interno', 'docente', 'administrativo')
                            THEN COALESCE(NULLIF(trim(facultad), ''), 'Facultad no especificada')
                        WHEN lower(trim(tipo_usuario)) = 'trabajador interno'
                            THEN 'Trabajador interno'
                        ELSE COALESCE(NULLIF(trim(tipo_usuario), ''), 'Sin especificar')
                    END AS source,
                    COUNT(*) AS total
                FROM access_logs
                WHERE date(accessed_at) BETWEEN ? AND ?
                GROUP BY period, origin, source
                ORDER BY period, origin, source
                """,
                (start.isoformat(), end.isoformat()),
            ).fetchall()
            return self._as_dicts(rows)

    def get_access_report_catalog(self) -> dict[str, list[str]]:
        """Devuelve universidades y facultades registradas o presentes en el historial.

        El catálogo permite distinguir entidades con cero accesos dentro del rango
        solicitado sin inventar universidades o facultades que no estén registradas.
        """
        with self.connection() as connection:
            universities = connection.execute(
                """
                SELECT name
                FROM (
                    SELECT TRIM(universidad) AS name
                    FROM external_users
                    WHERE lower(trim(tipo_usuario)) IN
                          ('estudiante externo', 'estudiante')
                      AND TRIM(universidad) <> ''
                    UNION
                    SELECT TRIM(universidad_externa) AS name
                    FROM access_logs
                    WHERE lower(trim(tipo_usuario)) IN
                          ('estudiante externo', 'estudiante')
                      AND TRIM(universidad_externa) <> ''
                )
                ORDER BY name COLLATE NOCASE
                """
            ).fetchall()
            faculties = connection.execute(
                """
                SELECT name
                FROM (
                    SELECT TRIM(facultad) AS name
                    FROM internal_students
                    WHERE TRIM(facultad) <> ''
                    UNION
                    SELECT TRIM(facultad) AS name
                    FROM internal_staff
                    WHERE TRIM(facultad) <> ''
                    UNION
                    SELECT TRIM(facultad) AS name
                    FROM access_logs
                    WHERE lower(trim(tipo_usuario)) IN
                          ('alumno interno', 'docente', 'administrativo')
                      AND TRIM(facultad) <> ''
                )
                ORDER BY name COLLATE NOCASE
                """
            ).fetchall()

        return {
            "universities": [str(row["name"]) for row in universities],
            "faculties": [str(row["name"]) for row in faculties],
        }

    def list_received_logins(self, limit: int | None = 1000) -> list[dict]:
        """Lista los eventos más recientes que el servidor central ha recibido."""
        with self.connection() as connection:
            if limit is None:
                rows = connection.execute(
                    """
                    SELECT id, received_at, kiosk_name, client_ip, identifier,
                           user_type, action, result, message
                    FROM received_logins
                    ORDER BY id DESC
                    """
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT id, received_at, kiosk_name, client_ip, identifier,
                           user_type, action, result, message
                    FROM received_logins
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (max(1, int(limit)),),
                ).fetchall()
            return self._as_dicts(rows)

    def record_received_login(
        self,
        *,
        kiosk_name: str = "",
        client_ip: str = "",
        identifier: str = "",
        user_type: str = "",
        action: str = "login",
        result: str = "",
        message: str = "",
    ) -> int:
        """Guarda un evento de login/registro recibido y devuelve su id.

        El futuro endpoint central puede llamar este método cada vez que procese
        una solicitud de un cliente. Se mantiene separado de la interfaz.
        """
        with self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO received_logins
                    (kiosk_name, client_ip, identifier, user_type, action, result, message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    kiosk_name.strip(),
                    client_ip.strip(),
                    identifier.strip(),
                    user_type.strip(),
                    action.strip(),
                    result.strip(),
                    message.strip(),
                ),
            )
            return int(cursor.lastrowid)

    def count_received_logins(self) -> dict:
        """Cuenta todos los eventos y calcula subtotales por tipo y resultado."""
        with self.connection() as connection:
            total = connection.execute(
                "SELECT COUNT(*) FROM received_logins"
            ).fetchone()[0]
            by_type = connection.execute(
                """
                SELECT
                    COALESCE(NULLIF(user_type, ''), 'Sin especificar') AS label,
                    COUNT(*) AS total
                FROM received_logins
                GROUP BY label
                ORDER BY total DESC, label
                """
            ).fetchall()
            by_result = connection.execute(
                """
                SELECT
                    COALESCE(NULLIF(result, ''), 'Sin especificar') AS label,
                    COUNT(*) AS total
                FROM received_logins
                GROUP BY label
                ORDER BY total DESC, label
                """
            ).fetchall()

            return {
                "total": int(total),
                "by_type": self._as_dicts(by_type),
                "by_result": self._as_dicts(by_result),
            }
