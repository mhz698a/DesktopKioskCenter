"""Pruebas de persistencia aisladas: python -m unittest discover -s tests."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from database import Database


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.legacy_dir = self.root / "legacy"
        self.legacy_dir.mkdir()
        self.db = Database(
            db_path=self.root / "appdata" / "desktopkioskcenter.sqlite3",
            legacy_dir=self.legacy_dir,
        )
        self.db.initialize()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_kiosk_status_catalog_is_seeded_and_maintainable(self):
        labels = {
            item["status_code"]: item["label"]
            for item in self.db.list_kiosk_status_codes()
        }
        self.assertEqual(labels, {
            0: "Sin conexión",
            1: "Disponible",
            2: "En uso",
            3: "Inactividad",
        })

        self.assertTrue(self.db.update_kiosk_status_label(2, "En uso activo"))
        self.assertEqual(self.db.get_kiosk_status_label(2), "En uso activo")
        with self.assertRaises(ValueError):
            self.db.update_kiosk_status_label(2, "   ")

    def test_internal_student_is_saved_and_expediente_is_unique(self):
        record = {
            "nombres": "Ana",
            "apellidos": "Pérez",
            "email": "ana@example.com",
            "facultad": "Facultad de Informática",
            "expediente": "12345",
        }
        self.db.add_internal_student(record)
        self.assertEqual(len(self.db.list_internal_students()), 1)
        self.assertEqual(self.db.list_internal_students()[0]["email"], "ana@example.com")

        with self.assertRaises(sqlite3.IntegrityError):
            self.db.add_internal_student({**record, "email": "otra@example.com"})

    def test_email_is_unique_across_internal_and_external_users(self):
        self.db.add_internal_student({
            "nombres": "Ana", "apellidos": "Prueba",
            "email": "Ana@example.com", "facultad": "Facultad de Informática",
            "expediente": "10001",
        })
        self.assertTrue(self.db.email_exists("ana@EXAMPLE.com"))
        self.assertTrue(self.db.find_registered_user("ANA@example.com"))
        self.assertEqual(
            self.db.find_registered_user("ANA@example.com")["expediente"], "10001"
        )

        with self.assertRaises(sqlite3.IntegrityError):
            self.db.add_external_user({
                "nombres": "Otra", "apellidos": "Persona",
                "email": "ANA@example.com", "tipo_usuario": "Público en general",
                "universidad": "",
            })

        with self.assertRaises(sqlite3.IntegrityError):
            self.db.add_internal_student({
                "nombres": "Otra", "apellidos": "Persona",
                "email": "ana@example.com", "facultad": "Facultad de Artes",
                "expediente": "10002",
            })

    def test_external_user_without_university_keeps_it_empty(self):
        self.db.add_external_user({
            "nombres": "Luis",
            "apellidos": "López",
            "email": "luis@example.com",
            "tipo_usuario": "Público en general",
            "universidad": "Universidad de ejemplo",
        })
        saved = self.db.list_external_users()[0]
        self.assertEqual(saved["universidad"], "")
        self.assertEqual(saved["email"], "luis@example.com")

    def test_received_login_can_be_listed_and_counted(self):
        self.db.record_received_login(
            kiosk_name="PC 1",
            client_ip="192.168.100.10",
            identifier="12345",
            user_type="Alumno interno",
            action="login",
            result="autorizado",
            message="Acceso permitido",
        )
        self.assertEqual(len(self.db.list_received_logins()), 1)
        totals = self.db.count_received_logins()
        self.assertEqual(totals["total"], 1)
        self.assertEqual(totals["by_result"][0]["label"], "autorizado")

    def test_student_and_external_user_can_be_updated_and_deleted(self):
        student_id = self.db.add_internal_student({
            "nombres": "Ana", "apellidos": "Pérez",
            "email": "ana@example.com",
            "facultad": "Facultad de Artes", "expediente": "123",
        })
        self.assertTrue(self.db.update_internal_student(student_id, {
            "nombres": "María", "apellidos": "Pérez",
            "email": "maria@example.com",
            "facultad": "Facultad de Derecho", "expediente": "456",
        }))
        self.assertEqual(self.db.list_internal_students()[0]["expediente"], "456")
        self.assertTrue(self.db.delete_internal_student(student_id))
        self.assertEqual(self.db.list_internal_students(), [])

        user_id = self.db.add_external_user({
            "nombres": "Luis", "apellidos": "López", "email": "luis@example.com",
            "tipo_usuario": "Estudiante Externo", "universidad": "Universidad X",
        })
        self.assertTrue(self.db.update_external_user(user_id, {
            "nombres": "Luis", "apellidos": "López", "email": "luis@example.com",
            "tipo_usuario": "Público en general", "universidad": "Universidad X",
        }))
        self.assertEqual(self.db.list_external_users()[0]["universidad"], "")
        self.assertTrue(self.db.delete_external_user(user_id))
        self.assertEqual(self.db.list_external_users(), [])

    def test_access_logs_can_be_listed_and_counted(self):
        self.db.record_access_log(
            kiosk_name="Kiosco A", nombres="Ana", apellidos="Pérez",
            expediente="12345", facultad="Facultad de Artes",
            universidad_externa="", tipo_usuario="Alumno interno",
        )
        records = self.db.list_access_logs()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["kiosk_name"], "Kiosco A")
        totals = self.db.count_access_logs()
        self.assertEqual(totals["total"], 1)
        self.assertEqual(totals["by_type"][0]["label"], "Alumno interno")
        self.assertEqual(totals["by_kiosk"][0]["label"], "Kiosco A")

    def test_external_user_requires_valid_email(self):
        with self.assertRaises(ValueError):
            self.db.add_external_user({
                "nombres": "Ana", "apellidos": "Prueba",
                "tipo_usuario": "Estudiante Externo", "universidad": "Universidad X",
            })
        with self.assertRaises(ValueError):
            self.db.add_external_user({
                "nombres": "Ana", "apellidos": "Prueba", "email": "no-es-email",
                "tipo_usuario": "Estudiante Externo", "universidad": "Universidad X",
            })

    def test_existing_database_schema_gains_email_column(self):
        old_path = self.root / "old-schema.sqlite3"
        import sqlite3
        with sqlite3.connect(old_path) as connection:
            connection.execute("""
                CREATE TABLE external_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombres TEXT NOT NULL,
                    apellidos TEXT NOT NULL,
                    tipo_usuario TEXT NOT NULL,
                    universidad TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                )
            """)
            connection.execute("""
                CREATE TABLE internal_students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombres TEXT NOT NULL,
                    apellidos TEXT NOT NULL,
                    facultad TEXT NOT NULL,
                    expediente TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                )
            """)
        upgraded = Database(old_path, self.legacy_dir)
        upgraded.initialize()
        with upgraded.connection() as connection:
            external_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(external_users)")
            }
            internal_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(internal_students)")
            }
        self.assertIn("email", external_columns)
        self.assertIn("email", internal_columns)

    def test_legacy_json_is_imported_once(self):
        student_file = self.legacy_dir / "internal_students.json"
        student_file.write_text(
            json.dumps([{
                "nombres": "María",
                "apellidos": "García",
                "facultad": "Facultad de Artes",
                "expediente": "98765",
            }], ensure_ascii=False),
            encoding="utf-8",
        )
        database_path = self.root / "migrated.sqlite3"
        migrated = Database(database_path, self.legacy_dir)
        migrated.initialize()
        migrated.initialize()
        students = migrated.list_internal_students()
        self.assertEqual(len(students), 1)
        self.assertEqual(students[0]["expediente"], "98765")


if __name__ == "__main__":
    unittest.main()
