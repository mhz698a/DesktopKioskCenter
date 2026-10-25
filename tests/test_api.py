"""Pruebas del contrato REST sin abrir sockets TCP."""
import tempfile
import unittest
from pathlib import Path

from api_server import create_api_app
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

    def test_invalid_action_returns_400_json(self):
        response = self.client.post("/api/v1/users/register/alumno", json={
            "action": "wrong", "data": {},
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.get_json())
