"""Pruebas del contrato REST sin abrir sockets TCP."""
import tempfile
import threading
import time
import unittest
from pathlib import Path

from api_server import ApiServer, create_api_app
from database import Database


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.db = Database(db_path=root / "test.sqlite3", legacy_dir=root / "legacy")
        self.db.initialize()
        self.client = create_api_app(self.db).test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_student_registers_and_duplicate_returns_409(self):
        payload = {
            "action": "registro_alumno",
            "data": {
                "nombres": "Example Example",
                "apellidos": "Example Prueba",
                "facultad": "Facultad de Filosofía",
                "expediente": "123456",
            },
        }
        first = self.client.post("/api/v1/users/register/alumno", json=payload)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.get_json(), {
            "unlocked": True, "message": "Registro de alumno completado con éxito."
        })

        # La solicitud debe persistir el usuario y ambos tipos de log en SQLite.
        self.assertEqual(self.db.list_internal_students()[0]["expediente"], "123456")
        received = self.db.list_received_logins()
        self.assertEqual(received[0]["action"], "registro_alumno")
        self.assertEqual(received[0]["result"], "registrado")
        access_logs = self.db.list_access_logs()
        self.assertEqual(access_logs[0]["expediente"], "123456")

        duplicate = self.client.post("/api/v1/users/register/alumno", json=payload)
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.get_json(), {
            "unlocked": False,
            "message": "El usuario ya se encuentra registrado con este expediente. Inicie sesión.",
        })

    def test_login_unknown_returns_401_and_registered_returns_200(self):
        payload = {"action": "unlock_login", "data": {"usuario": "123456", "contrasena": ".123456"}}
        unknown = self.client.post("/api/v1/auth-client-pc/login", json=payload)
        self.assertEqual(unknown.status_code, 401)
        self.assertEqual(unknown.get_json(), {
            "unlocked": False,
            "message": "El usuario no se ha registrado todavía. Por favor, realice su registro primero."
        })
        self.db.add_internal_student({
            "nombres": "Example", "apellidos": "Prueba",
            "facultad": "Facultad de Filosofía", "expediente": "123456",
        })
        registered = self.client.post("/api/v1/auth-client-pc/login", json=payload)
        self.assertEqual(registered.status_code, 200)
        self.assertEqual(registered.get_json(), {
            "unlocked": True, "message": "Sesión iniciada correctamente."
        })

        self.db.add_external_user({
            "nombres": "Extern", "apellidos": "Example",
            "email": "externo@example.com", "tipo_usuario": "Estudiante Externo",
            "universidad": "Universidad X",
        })
        email_login = self.client.post("/api/v1/auth-client-pc/login", json={
            "action": "unlock_login",
            "data": {"usuario": "EXTERNO@example.com", "contrasena": "cualquier-valor"},
        })
        self.assertEqual(email_login.status_code, 200)
        self.assertTrue(email_login.get_json()["unlocked"])

    def test_external_student_and_public_general_registration(self):
        external_student = self.client.post("/api/v1/users/register/externo", json={
            "action": "registro_externo",
            "data": {
                "nombres": "Ejemplo", "apellidos": "Prueba",
                "email": "estudiante@example.com",
                "tipo-usuario": "estudiante", "universidad-ext": "Universidad X",
            },
        })
        self.assertEqual(external_student.status_code, 201)
        saved = self.db.list_external_users()[0]
        self.assertEqual(saved["tipo_usuario"], "Estudiante Externo")
        self.assertEqual(saved["email"], "estudiante@example.com")
        duplicate_student = self.client.post("/api/v1/users/register/externo", json={
            "action": "registro_externo",
            "data": {
                "nombres": "Ejemplo", "apellidos": "Prueba",
                "email": "estudiante@example.com",
                "tipo-usuario": "estudiante", "universidad-ext": "Universidad X",
            },
        })
        self.assertEqual(duplicate_student.status_code, 409)
        self.assertFalse(duplicate_student.get_json()["unlocked"])

        public_general = self.client.post("/api/v1/users/register/externo", json={
            "action": "registro_externo",
            "data": {
                "nombres": "Publico", "apellidos": "General",
                "email": "publico@example.com", "tipo-usuario": "Público en general",
            },
        })
        self.assertEqual(public_general.status_code, 201)
        saved = self.db.list_external_users()[1]
        self.assertEqual(saved["tipo_usuario"], "Público en general")
        self.assertEqual(saved["email"], "publico@example.com")
        duplicate_public = self.client.post("/api/v1/users/register/externo", json={
            "action": "registro_externo",
            "data": {
                "nombres": "Publico", "apellidos": "General",
                "email": "publico@example.com", "tipo-usuario": "Público en general",
            },
        })
        self.assertEqual(duplicate_public.status_code, 409)
        self.assertFalse(duplicate_public.get_json()["unlocked"])

    def test_external_registration_requires_email_for_all_user_types(self):
        response = self.client.post("/api/v1/users/register/externo", json={
            "action": "registro_externo",
            "data": {
                "nombres": "Trabajador", "apellidos": "Ejemplo",
                "tipo-usuario": "Trabajador Interno",
            },
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["unlocked"])
        self.assertIn("email", response.get_json()["message"].lower())

        # Aunque el registro se rechace, la petición debe quedar auditada.
        rejected_log = self.db.list_received_logins()[0]
        self.assertEqual(rejected_log["action"], "registro_externo")
        self.assertEqual(rejected_log["result"], "validación fallida")

        worker = self.client.post("/api/v1/users/register/externo", json={
            "action": "registro_externo",
            "data": {
                "nombres": "Trabajador", "apellidos": "Ejemplo",
                "email": "trabajador@example.com",
                "tipo-usuario": "Trabajador Interno",
            },
        })
        self.assertEqual(worker.status_code, 201)
        self.assertEqual(self.db.list_external_users()[0]["email"], "trabajador@example.com")

    def test_post_health_records_heartbeat_by_remote_ip(self):
        response = self.client.post(
            "/api/v1/health",
            json={
                "action": "heartbeat",
                "data": {"status": 2, "time_string": "00:00:01"},
            },
            environ_base={"REMOTE_ADDR": "192.168.1.22"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

        heartbeat = self.db.get_kiosk_heartbeat("192.168.1.22")
        self.assertIsNotNone(heartbeat)
        self.assertEqual(heartbeat["status_code"], 2)
        self.assertEqual(heartbeat["status_label"], "En uso")
        self.assertEqual(heartbeat["time_string"], "00:00:01")

        # La IP se identifica por el socket de origen, no por un campo del JSON.
        self.assertIsNone(self.db.get_kiosk_heartbeat("10.0.0.50"))
        self.assertEqual(
            {item["status_code"]: item["label"] for item in self.db.list_kiosk_status_codes()},
            {0: "Sin conexión", 1: "Disponible", 2: "En uso", 3: "Inactividad"},
        )

    def test_get_health_is_removed_and_invalid_heartbeat_is_rejected(self):
        legacy_get = self.client.get("/api/v1/health")
        self.assertEqual(legacy_get.status_code, 405)

        invalid_status = self.client.post("/api/v1/health", json={
            "action": "heartbeat", "data": {"status": 0, "time_string": "00:00:01"},
        })
        self.assertEqual(invalid_status.status_code, 400)

        invalid_time = self.client.post("/api/v1/health", json={
            "action": "heartbeat", "data": {"status": 1, "time_string": "0:0:1"},
        })
        self.assertEqual(invalid_time.status_code, 400)

    def test_heartbeat_is_marked_offline_after_four_seconds(self):
        self.db.record_kiosk_heartbeat(
            client_ip="192.168.1.23",
            status_code=2,
            time_string="00:03:12",
            last_seen_at=100.0,
        )
        unchanged = self.db.mark_stale_kiosks_offline(timeout_seconds=4, now=103.99)
        self.assertEqual(unchanged, 0)
        changed = self.db.mark_stale_kiosks_offline(timeout_seconds=4, now=104.0)
        self.assertEqual(changed, 1)

        heartbeat = self.db.get_kiosk_heartbeat("192.168.1.23")
        self.assertEqual(heartbeat["status_code"], 0)
        self.assertEqual(heartbeat["status_label"], "Sin conexión")

    def test_server_monitor_marks_client_offline_without_another_request(self):
        client_ip = "192.168.1.24"
        self.db.record_kiosk_heartbeat(
            client_ip=client_ip,
            status_code=3,
            time_string="00:03:00",
            last_seen_at=time.time() - 4.5,
        )

        server = ApiServer(self.db, host="127.0.0.1", port=0)
        monitor = threading.Thread(target=server._monitor_stale_heartbeats)
        monitor.start()
        try:
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline:
                heartbeat = self.db.get_kiosk_heartbeat(client_ip)
                if heartbeat and heartbeat["status_code"] == 0:
                    break
                time.sleep(0.05)
        finally:
            server._heartbeat_monitor_stop.set()
            monitor.join(timeout=1.0)

        heartbeat = self.db.get_kiosk_heartbeat(client_ip)
        self.assertEqual(heartbeat["status_code"], 0)
        self.assertEqual(heartbeat["status_label"], "Sin conexión")

    def test_invalid_action_returns_400_json(self):
        response = self.client.post("/api/v1/users/register/alumno", json={
            "action": "wrong", "data": {},
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.get_json())
