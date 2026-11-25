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

    def test_access_report_groups_by_day_week_and_month_and_filters_dates(self):
        self.db.record_access_log(
            kiosk_name="PC 1", nombres="Ana", apellidos="Pérez",
            universidad_externa="Universidad X", tipo_usuario="Estudiante Externo",
            accessed_at="2026-11-02 09:00:00",
        )
        self.db.record_access_log(
            kiosk_name="PC 1", nombres="Luis", apellidos="López",
            tipo_usuario="Público en general", accessed_at="2026-11-03 10:00:00",
        )
        self.db.record_access_log(
            kiosk_name="PC 2", nombres="Eva", apellidos="García",
            universidad_externa="Universidad X", tipo_usuario="Estudiante Externo",
            accessed_at="2026-11-10 11:00:00",
        )
        daily = self.db.generate_access_report("2026-11-01", "2026-11-05", "day")
        self.assertEqual(len(daily), 2)
        self.assertEqual({row["period"] for row in daily}, {"2026-11-02", "2026-11-03"})
        self.assertEqual(
            {(row["origin"], row["source"], row["total"]) for row in daily},
            {("Universidad", "Universidad X", 1),
             ("Público en general", "Público en general", 1)},
        )
        weekly = self.db.generate_access_report("2026-11-01", "2026-11-05", "week")
        self.assertEqual({row["period"] for row in weekly}, {"2026-11-02"})
        self.assertEqual(sum(row["total"] for row in weekly), 2)
        monthly = self.db.generate_access_report("2026-11-01", "2026-11-30", "month")
        self.assertEqual({row["period"] for row in monthly}, {"2026-11"})
        self.assertEqual(sum(row["total"] for row in monthly), 3)
        with self.assertRaises(ValueError):
            self.db.generate_access_report("2026-11-05", "2026-11-01", "day")
        with self.assertRaises(ValueError):
            self.db.generate_access_report("2026-11-01", "2026-11-05", "year")


    def test_access_report_catalog_includes_registered_and_historical_entities(self):
        self.db.add_internal_student({
            "nombres": "Ana",
            "apellidos": "Pérez",
            "email": "ana.catalog@example.com",
            "facultad": "Facultad de Derecho",
            "expediente": "CAT001",
        })
        self.db.add_external_user({
            "nombres": "Luis",
            "apellidos": "López",
            "email": "luis.catalog@example.com",
            "tipo_usuario": "Estudiante Externo",
            "universidad": "Universidad Y",
        })
        self.db.record_access_log(
            kiosk_name="PC 1",
            nombres="Eva",
            apellidos="García",
            facultad="Facultad de Informática",
            tipo_usuario="Alumno interno",
            accessed_at="2026-11-02 09:00:00",
        )
        self.db.record_access_log(
            kiosk_name="PC 2",
            nombres="Mario",
            apellidos="Díaz",
            universidad_externa="Universidad X",
            tipo_usuario="Estudiante Externo",
            accessed_at="2026-11-02 10:00:00",
        )

        catalog = self.db.get_access_report_catalog()
        self.assertEqual(
            catalog["universities"],
            ["Universidad X", "Universidad Y"],
        )
        self.assertEqual(
            catalog["faculties"],
            ["Facultad de Derecho", "Facultad de Informática"],
        )

    def test_manual_student_unlock_records_simulated_registration_and_access(self):
        student_id = self.db.add_internal_student({
            "nombres": "Ana", "apellidos": "Pérez", "email": "ana@example.com",
            "facultad": "Facultad de Informática", "expediente": "12345",
        })
        student = next(
            item for item in self.db.list_internal_students()
            if item["id"] == student_id
        )
        result = self.db.record_manual_student_unlock(
            kiosk_name="PC Entrega 1", client_ip="192.168.100.20", student=student,
        )
        self.assertEqual(
            set(result), {"registration_log_id", "unlock_log_id", "access_log_id"}
        )
        received = self.db.list_received_logins(limit=None)
        self.assertEqual(
            {item["action"] for item in received},
            {"registro_alumno_simulado", "unlock_login_simulado"},
        )
        self.assertTrue(all("simulación" in item["result"] for item in received))
        access = self.db.list_access_logs(limit=None)
        self.assertEqual(len(access), 1)
        self.assertEqual(access[0]["kiosk_name"], "PC Entrega 1")
        self.assertEqual(access[0]["expediente"], "12345")
        self.assertEqual(access[0]["tipo_usuario"], "Alumno interno")


    def test_manual_staff_assignment_records_employee_number_and_staff_type(self):
        result = self.db.record_manual_user_session(
            kiosk_name="PC-Staff",
            client_ip="192.168.1.44",
            user={
                "id": 1,
                "nombres": "Laura",
                "apellidos": "Gómez",
                "email": "laura.staff@example.com",
                "tipo_usuario": "Administrativo",
                "facultad": "Facultad de Derecho",
                "numero_empleado": "556677",
                "expediente": "556677",
            },
        )
        self.assertGreater(result["registration_log_id"], 0)
        self.assertGreater(result["unlock_log_id"], 0)
        self.assertGreater(result["access_log_id"], 0)

        received = self.db.list_received_logins()
        self.assertEqual(received[0]["action"], "unlock_login_simulado")
        self.assertEqual(received[0]["identifier"], "556677")
        self.assertEqual(received[0]["user_type"], "Administrativo")
        self.assertEqual(received[1]["action"], "registro_personal_simulado")

        access = self.db.list_access_logs()[0]
        self.assertEqual(access["expediente"], "556677")
        self.assertEqual(access["tipo_usuario"], "Administrativo")
        self.assertEqual(access["facultad"], "Facultad de Derecho")

    def test_manual_public_general_assignment_records_public_session(self):
        user_id = self.db.add_external_user({
            "nombres": "Luis",
            "apellidos": "Pérez",
            "email": "luis.publico@example.com",
            "tipo_usuario": "Público en general",
            "universidad": "",
        })
        user = next(
            item for item in self.db.list_external_users()
            if item["id"] == user_id
        )
        result = self.db.record_manual_user_session(
            kiosk_name="PC Público 1",
            client_ip="192.168.100.30",
            user=user,
        )

        self.assertIn("access_log_id", result)
        access = self.db.list_access_logs(limit=None)
        self.assertEqual(len(access), 1)
        self.assertEqual(access[0]["tipo_usuario"], "Público en general")
        self.assertEqual(access[0]["nombres"], "Luis")
        self.assertEqual(access[0]["universidad_externa"], "")

        received = self.db.list_received_logins(limit=None)
        self.assertEqual(
            {item["action"] for item in received},
            {"registro_usuario_simulado", "unlock_login_simulado"},
        )
        self.assertTrue(
            all("simulación administrativa" in item["result"] for item in received)
        )

    def test_deleting_configured_kiosk_heartbeats_only_removes_matching_ips(self):
        self.db.record_kiosk_heartbeat(
            client_ip="192.168.100.10", status_code=1, time_string="00:00:01"
        )
        self.db.record_kiosk_heartbeat(
            client_ip="192.168.100.11", status_code=2, time_string="00:00:02"
        )
        removed = self.db.delete_kiosk_heartbeats(["192.168.100.10"])
        self.assertEqual(removed, 1)
        self.assertIsNone(self.db.get_kiosk_heartbeat("192.168.100.10"))
        self.assertIsNotNone(self.db.get_kiosk_heartbeat("192.168.100.11"))

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



    def test_internal_staff_crud_employee_login_identifier_and_unique_number(self):
        record = {
            "nombres": "Laura",
            "apellidos": "Gómez",
            "email": "laura.staff@example.com",
            "tipo_usuario": "Docente",
            "facultad": "Facultad de Ingeniería",
            "numero_empleado": "778899",
        }
        staff_id = self.db.add_internal_staff(record)
        staff = next(
            row for row in self.db.list_internal_staff()
            if row["id"] == staff_id
        )
        self.assertEqual(staff["numero_empleado"], "778899")
        self.assertEqual(staff["expediente"], "778899")
        self.assertEqual(self.db.find_registered_user("778899")["tipo_usuario"], "Docente")
        self.assertEqual(
            self.db.find_registered_user("LAURA.STAFF@example.com")["numero_empleado"],
            "778899",
        )

        with self.assertRaises(sqlite3.IntegrityError):
            self.db.add_internal_staff({
                **record,
                "nombres": "Otra",
                "email": "otra.staff@example.com",
            })

        with self.assertRaises(sqlite3.IntegrityError):
            self.db.add_internal_student({
                "nombres": "Alumno",
                "apellidos": "Con número repetido",
                "email": "alumno.staff@example.com",
                "facultad": "Facultad de Artes",
                "expediente": "778899",
            })

        self.assertTrue(self.db.update_internal_staff(staff_id, {
            **record,
            "tipo_usuario": "Administrativo",
            "numero_empleado": "990011",
        }))
        updated = self.db.find_registered_user("990011")
        self.assertEqual(updated["tipo_usuario"], "Administrativo")
        self.assertTrue(self.db.delete_internal_staff(staff_id))
        self.assertIsNone(self.db.find_registered_user("990011"))

    def test_faculty_catalog_removals_persist_after_database_reinitialization(self):
        faculty = "Facultad de Química"
        self.assertIn(faculty, self.db.list_faculties())
        self.assertTrue(self.db.delete_faculty(faculty))
        self.db.initialize()
        self.assertNotIn(faculty, self.db.list_faculties())

    def test_faculty_catalog_add_rename_and_protect_faculties_in_use(self):
        self.assertIn("Facultad de Artes", self.db.list_faculties())
        self.assertTrue(self.db.add_faculty("Escuela de Ciencias"))
        self.assertFalse(self.db.add_faculty("escuela de ciencias"))

        student_id = self.db.add_internal_student({
            "nombres": "Ana", "apellidos": "Pérez",
            "email": "ana.faculty@example.com",
            "facultad": "Facultad de Artes", "expediente": "F001",
        })
        staff_id = self.db.add_internal_staff({
            "nombres": "Luis", "apellidos": "García",
            "email": "luis.faculty@example.com",
            "tipo_usuario": "Administrativo",
            "facultad": "Facultad de Artes", "numero_empleado": "F002",
        })
        self.db.record_access_log(
            nombres="Ana",
            apellidos="Pérez",
            expediente="F001",
            facultad="Facultad de Artes",
            tipo_usuario="Alumno interno",
            accessed_at="2026-11-20 09:00:00",
        )

        self.assertTrue(
            self.db.rename_faculty("Facultad de Artes", "Facultad de Artes y Diseño")
        )
        self.assertEqual(
            self.db.list_internal_students()[0]["facultad"],
            "Facultad de Artes y Diseño",
        )
        self.assertEqual(
            next(x for x in self.db.list_internal_staff() if x["id"] == staff_id)["facultad"],
            "Facultad de Artes y Diseño",
        )
        self.assertEqual(
            self.db.list_access_logs(limit=None)[0]["facultad"],
            "Facultad de Artes y Diseño",
        )
        with self.assertRaises(ValueError):
            self.db.delete_faculty("Facultad de Artes y Diseño")

        self.assertTrue(self.db.delete_internal_student(student_id))
        self.assertTrue(self.db.delete_internal_staff(staff_id))
        self.assertTrue(self.db.delete_faculty("Facultad de Artes y Diseño"))
        self.assertNotIn("Facultad de Artes y Diseño", self.db.list_faculties())

    def test_statistics_include_teachers_and_administrators_by_faculty(self):
        self.db.record_access_log(
            nombres="Docente", apellidos="Ejemplo",
            expediente="1001", facultad="Facultad de Informática",
            tipo_usuario="Docente",
            accessed_at="2026-11-21 09:00:00",
        )
        self.db.record_access_log(
            nombres="Administrativa", apellidos="Ejemplo",
            expediente="1002", facultad="Facultad de Derecho",
            tipo_usuario="Administrativo",
            accessed_at="2026-11-21 10:00:00",
        )
        rows = self.db.generate_access_report("2026-11-21", "2026-11-21", "day")
        self.assertEqual(
            {(row["origin"], row["source"], row["total"]) for row in rows},
            {
                ("UAQ", "Facultad de Informática", 1),
                ("UAQ", "Facultad de Derecho", 1),
            },
        )
        catalog = self.db.get_access_report_catalog()
        self.assertIn("Facultad de Informática", catalog["faculties"])
        self.assertIn("Facultad de Derecho", catalog["faculties"])

if __name__ == "__main__":
    unittest.main()
