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
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from const import BASE_DIR, DATABASE_FILE


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
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                );

                CREATE TABLE IF NOT EXISTS external_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombres TEXT NOT NULL,
                    apellidos TEXT NOT NULL,
                    tipo_usuario TEXT NOT NULL,
                    universidad TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                );

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

        self._migrate_legacy_json()

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

    def list_internal_students(self) -> list[dict]:
        """Devuelve los alumnos internos en orden de alta."""
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT id, nombres, apellidos, facultad, expediente, created_at
                FROM internal_students
                ORDER BY id
                """
            ).fetchall()
            return self._as_dicts(rows)

    def add_internal_student(self, record: dict) -> int:
        """Inserta un alumno y devuelve su id; expediente no puede repetirse."""
        with self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO internal_students
                    (nombres, apellidos, facultad, expediente)
                VALUES (?, ?, ?, ?)
                """,
                (
                    record["nombres"].strip(),
                    record["apellidos"].strip(),
                    record["facultad"].strip(),
                    record["expediente"].strip(),
                ),
            )
            return int(cursor.lastrowid)

    def list_external_users(self) -> list[dict]:
        """Devuelve los usuarios externos y público general en orden de alta."""
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT id, nombres, apellidos, tipo_usuario, universidad, created_at
                FROM external_users
                ORDER BY id
                """
            ).fetchall()
            return self._as_dicts(rows)

    def add_external_user(self, record: dict) -> int:
        """Inserta un registro de usuario general; universidad puede quedar vacía."""
        tipo_usuario = record["tipo_usuario"].strip()
        universidad = record.get("universidad", "").strip()
        if tipo_usuario != "Estudiante Externo":
            # Solo un estudiante externo debe quedar vinculado a una universidad.
            universidad = ""

        with self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO external_users
                    (nombres, apellidos, tipo_usuario, universidad)
                VALUES (?, ?, ?, ?)
                """,
                (
                    record["nombres"].strip(),
                    record["apellidos"].strip(),
                    tipo_usuario,
                    universidad,
                ),
            )
            return int(cursor.lastrowid)

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
