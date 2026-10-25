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

    def test_internal_student_is_saved_and_expediente_is_unique(self):
        record = {
            "nombres": "Ana",
            "apellidos": "Pérez",
            "facultad": "Facultad de Informática",
            "expediente": "12345",
        }
        self.db.add_internal_student(record)
        self.assertEqual(len(self.db.list_internal_students()), 1)

        with self.assertRaises(sqlite3.IntegrityError):
            self.db.add_internal_student(record)

    def test_external_user_without_university_keeps_it_empty(self):
        self.db.add_external_user({
            "nombres": "Luis",
            "apellidos": "López",
            "tipo_usuario": "Público en general",
            "universidad": "Universidad de ejemplo",
        })
        saved = self.db.list_external_users()[0]
        self.assertEqual(saved["universidad"], "")

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
