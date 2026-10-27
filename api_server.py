"""API REST de DesktopKioskCenter para registro y comprobación de usuarios."""
import logging
import os
import re
import sqlite3
import threading

from flask import Flask, g, jsonify, request
from werkzeug.serving import make_server

from database import Database

logger = logging.getLogger(__name__)

LOGIN_UNKNOWN_MESSAGE = "El correo electrónico o expediente no está registrado. Realice su registro primero."
DUPLICATE_MESSAGE = "El correo electrónico ya se encuentra registrado. Inicie sesión."
DUPLICATE_STUDENT_MESSAGE = "El correo electrónico o expediente ya se encuentra registrado. Inicie sesión."
STUDENT_REGISTERED_MESSAGE = "Registro de alumno completado con éxito."
EXTERNAL_REGISTERED_MESSAGE = "Registro de usuario completado con éxito."
EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def create_api_app(database: Database) -> Flask:
    """Crea la app Flask para servirla o probarla sin abrir un puerto TCP."""
    app = Flask("DesktopKioskCenterAPI")

    def response(unlocked: bool, message: str, status: int):
        return jsonify({"unlocked": unlocked, "message": message}), status

    def parse_payload(expected_action: str):
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return None, response(False, "El cuerpo debe ser un objeto JSON válido.", 400)
        if body.get("action") != expected_action:
            return None, response(False, "La acción enviada no es válida.", 400)
        data = body.get("data")
        if not isinstance(data, dict):
            return None, response(False, "El campo «data» debe ser un objeto JSON.", 400)
        return data, None

    def kiosk_name():
        return (request.headers.get("X-Kiosk-Name") or "Cliente API").strip()[:200]

    def safe_request_log(identifier, user_type, action, result, message):
        # Marca el evento para que after_request no lo registre por duplicado.
        g.received_log_recorded = True
        # No guardar contrasena ni volcar el cuerpo de la petición a los logs.
        try:
            database.record_received_login(
                kiosk_name=kiosk_name(),
                client_ip=(request.remote_addr or "")[:64],
                identifier=str(identifier or "")[:255],
                user_type=str(user_type or "")[:100],
                action=str(action or "")[:100],
                result=str(result or "")[:100],
                message=str(message or "")[:500],
            )
        except Exception:
            logger.exception("No se pudo guardar el log de una petición REST.")

    def safe_access_log(record, fallback_identifier=""):
        try:
            database.record_access_log(
                kiosk_name=kiosk_name(),
                nombres=str(record.get("nombres", "") or ""),
                apellidos=str(record.get("apellidos", "") or ""),
                expediente=str(record.get("expediente", "") or fallback_identifier or ""),
                facultad=str(record.get("facultad", "") or ""),
                universidad_externa=str(record.get("universidad", "") or ""),
                tipo_usuario=str(record.get("tipo_usuario", "") or ""),
            )
        except Exception:
            logger.exception("No se pudo guardar el log de un acceso REST.")

    @app.post("/api/v1/auth-client-pc/login")
    def login():
        data, error = parse_payload("unlock_login")
        if error:
            return error
        # El identificador es email o expediente; nunca se busca por nombres.
        identifier = str(data.get("identificador", data.get("usuario", data.get("email", ""))) or "").strip()
        password = str(data.get("contrasena", "") or "")
        if not identifier or not password:
            return response(False, "Los campos «usuario» y «contrasena» son obligatorios.", 400)

        user = database.find_registered_user(identifier)
        if user is None:
            safe_request_log(identifier, "", "unlock_login", "no registrado", LOGIN_UNKNOWN_MESSAGE)
            return response(False, LOGIN_UNKNOWN_MESSAGE, 401)

        safe_request_log(identifier, user.get("tipo_usuario", ""), "unlock_login", "registrado", "Sesión iniciada correctamente.")
        safe_access_log(user, fallback_identifier=identifier)
        return response(True, "Sesión iniciada correctamente.", 200)

    @app.post("/api/v1/users/register/alumno")
    def register_student():
        data, error = parse_payload("registro_alumno")
        if error:
            return error
        names = str(data.get("nombres", "") or "").strip()
        surnames = str(data.get("apellidos", "") or "").strip()
        email = str(data.get("email", "") or "").strip()
        faculty = str(data.get("facultad", "") or "").strip()
        expediente = str(data.get("expediente", "") or "").strip()
        if (
            not names or not surnames or not faculty
            or not expediente.isdigit()
            or not all(c.isalpha() or c == " " for c in names)
            or not all(c.isalpha() or c == " " for c in surnames)
        ):
            return response(False, "Los datos del alumno son inválidos o están incompletos.", 400)
        if not email or not EMAIL_RE.fullmatch(email):
            return response(False, "Ingresa un correo electrónico válido; es obligatorio para registrar al alumno.", 400)

        record = {
            "nombres": names,
            "apellidos": surnames,
            "email": email,
            "facultad": faculty,
            "expediente": expediente,
        }
        if database.email_exists(email):
            safe_request_log(email, "Alumno interno", "registro_alumno", "duplicado", DUPLICATE_STUDENT_MESSAGE)
            return response(False, DUPLICATE_STUDENT_MESSAGE, 409)
        try:
            database.add_internal_student(record)
        except sqlite3.IntegrityError:
            safe_request_log(email, "Alumno interno", "registro_alumno", "duplicado", DUPLICATE_STUDENT_MESSAGE)
            return response(False, DUPLICATE_STUDENT_MESSAGE, 409)
        except sqlite3.Error:
            logger.exception("Falló el registro de un alumno.")
            return response(False, "No se pudo completar el registro por un error de almacenamiento.", 500)

        safe_request_log(expediente, "Alumno interno", "registro_alumno", "registrado", STUDENT_REGISTERED_MESSAGE)
        safe_access_log({**record, "tipo_usuario": "Alumno interno"}, fallback_identifier=expediente)
        return response(True, STUDENT_REGISTERED_MESSAGE, 201)

    @app.post("/api/v1/users/register/externo")
    def register_external():
        data, error = parse_payload("registro_externo")
        if error:
            return error

        names = str(data.get("nombres", "") or "").strip()
        surnames = str(data.get("apellidos", "") or "").strip()
        email = str(data.get("email", "") or "").strip()
        raw_type = str(data.get("tipo-usuario", data.get("tipo_usuario", "")) or "").strip().casefold()
        university = str(data.get("universidad-ext", data.get("universidad", "")) or "").strip()

        if (
            not names or not surnames
            or not all(c.isalpha() or c == " " for c in names)
            or not all(c.isalpha() or c == " " for c in surnames)
        ):
            return response(False, "Los nombres y apellidos son obligatorios y solo admiten letras y espacios.", 400)
        if not email:
            return response(False, "El campo «email» es obligatorio para todos los usuarios externos.", 400)
        if not EMAIL_RE.fullmatch(email):
            return response(False, "Ingresa una dirección de email válida.", 400)

        if raw_type in ("estudiante", "estudiante externo", "estudiante_externo"):
            user_type = "Estudiante Externo"
        elif raw_type in ("público en general", "publico en general", "publico_general", "publico", "general"):
            user_type = "Público en general"
        elif raw_type in ("trabajador interno", "trabajador_interno", "trabajador"):
            user_type = "Trabajador Interno"
        else:
            return response(False, "El campo «tipo-usuario» no contiene un tipo reconocido.", 400)

        if user_type == "Estudiante Externo" and not university:
            return response(False, "El campo «universidad-ext» es obligatorio para Estudiante Externo.", 400)

        record = {
            "nombres": names, "apellidos": surnames, "email": email,
            "tipo_usuario": user_type,
            "universidad": university if user_type == "Estudiante Externo" else "",
        }
        if database.external_user_exists(record):
            safe_request_log(email or names, user_type, "registro_externo", "duplicado", DUPLICATE_MESSAGE)
            return response(False, DUPLICATE_MESSAGE, 409)
        try:
            database.add_external_user(record)
        except sqlite3.IntegrityError:
            safe_request_log(email or names, user_type, "registro_externo", "duplicado", DUPLICATE_MESSAGE)
            return response(False, DUPLICATE_MESSAGE, 409)
        except sqlite3.Error:
            logger.exception("Falló el registro de un usuario externo.")
            return response(False, "No se pudo completar el registro por un error de almacenamiento.", 500)

        safe_request_log(email or names, user_type, "registro_externo", "registrado", EXTERNAL_REGISTERED_MESSAGE)
        safe_access_log(record)
        return response(True, EXTERNAL_REGISTERED_MESSAGE, 201)

    @app.get("/ping")
    def ping():
        return jsonify({"status": "ok"}), 200

    @app.post("/api/v1/health")
    def health():
        """Recibe el heartbeat del cliente y registra su IP de origen."""
        data, error = parse_payload("heartbeat")
        if error:
            return error

        status_code = data.get("status")
        if isinstance(status_code, bool) or not isinstance(status_code, int):
            return jsonify({"status": "error", "message": "data.status debe ser un entero."}), 400
        if status_code not in (1, 2, 3):
            return jsonify({
                "status": "error",
                "message": "El cliente solo puede reportar los estados 1, 2 o 3.",
            }), 400

        time_string = data.get("time_string")
        if not isinstance(time_string, str) or not re.fullmatch(r"\d{2,}:[0-5]\d:[0-5]\d", time_string):
            return jsonify({
                "status": "error",
                "message": "data.time_string debe tener formato HH:MM:SS.",
            }), 400

        source_ip = request.remote_addr
        if not source_ip:
            return jsonify({"status": "error", "message": "No se pudo determinar la IP de origen."}), 400

        try:
            import ipaddress
            parsed_ip = ipaddress.ip_address(source_ip)
            if getattr(parsed_ip, "ipv4_mapped", None) is not None:
                source_ip = str(parsed_ip.ipv4_mapped)
            else:
                source_ip = str(parsed_ip)
            database.record_kiosk_heartbeat(
                client_ip=source_ip,
                status_code=status_code,
                time_string=time_string,
                kiosk_name=kiosk_name(),
            )
        except ValueError as exc:
            return jsonify({"status": "error", "message": str(exc)}), 400
        except sqlite3.Error:
            logger.exception("No se pudo guardar el heartbeat del kiosco.")
            return jsonify({"status": "error", "message": "No se pudo guardar el estado del kiosco."}), 500

        return jsonify({"status": "ok", "message": "Heartbeat recibido."}), 200

    @app.after_request
    def log_unrecorded_api_request(response):
        """Registra también peticiones funcionales rechazadas por validación."""
        route_actions = {
            "/api/v1/auth-client-pc/login": "unlock_login",
            "/api/v1/users/register/alumno": "registro_alumno",
            "/api/v1/users/register/externo": "registro_externo",
        }
        if request.method != "POST" or request.path not in route_actions:
            return response
        if getattr(g, "received_log_recorded", False):
            return response

        payload = request.get_json(silent=True)
        payload = payload if isinstance(payload, dict) else {}
        data = payload.get("data")
        data = data if isinstance(data, dict) else {}

        identifier = (
            data.get("usuario")
            or data.get("expediente")
            or data.get("email")
            or data.get("nombres")
            or ""
        )
        user_type = data.get("tipo-usuario") or data.get("tipo_usuario") or ""
        action = payload.get("action") or route_actions[request.path]
        status = response.status_code
        if 200 <= status < 300:
            result = "permitido" if request.path == "/api/v1/auth-client-pc/login" else "registrado"
        elif status == 400:
            result = "validación fallida"
        elif status == 401:
            result = "rechazado"
        elif status == 409:
            result = "duplicado"
        elif status >= 500:
            result = "error interno"
        else:
            result = f"HTTP {status}"

        body = response.get_json(silent=True)
        message = body.get("message", "") if isinstance(body, dict) else ""
        safe_request_log(identifier, user_type, action, result, message or f"HTTP {status}")
        return response

    return app


class ApiServer:
    """Servidor WSGI en segundo plano administrado por main.py."""

    def __init__(self, database: Database, host=None, port=None):
        self.host = host or os.environ.get("DESKTOPKIOSKCENTER_API_HOST", "0.0.0.0")
        self.port = int(port if port is not None else os.environ.get("DESKTOPKIOSKCENTER_API_PORT", "7085"))
        self.database = database
        self.app = create_api_app(database)
        self._server = None
        self._thread = None
        self._heartbeat_monitor_stop = threading.Event()
        self._heartbeat_monitor_thread = None

    def _monitor_stale_heartbeats(self):
        """Marca como offline a los clientes tras cuatro segundos sin heartbeat."""
        while not self._heartbeat_monitor_stop.wait(0.25):
            try:
                self.database.mark_stale_kiosks_offline(timeout_seconds=4.0)
            except Exception:
                logger.exception("No se pudo actualizar el estado de kioscos inactivos.")

    def start(self):
        if self._server is not None:
            return
        self._server = make_server(self.host, self.port, self.app, threaded=True)
        self._heartbeat_monitor_stop.clear()
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="DesktopKioskCenter-REST",
            daemon=True,
        )
        self._thread.start()
        self._heartbeat_monitor_thread = threading.Thread(
            target=self._monitor_stale_heartbeats,
            name="DesktopKioskCenter-HeartbeatMonitor",
            daemon=True,
        )
        self._heartbeat_monitor_thread.start()

    def stop(self):
        self._heartbeat_monitor_stop.set()
        if self._heartbeat_monitor_thread is not None:
            self._heartbeat_monitor_thread.join(timeout=2)
        self._heartbeat_monitor_thread = None
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=3)
        self._server = None
        self._thread = None
