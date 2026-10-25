# DesktopKioskCenter

Aplicación de escritorio PyQt6 para administrar clientes DesktopKiosk. La interfaz está organizada por pestañas; la persistencia de usuarios usa SQLite y la configuración de equipos usa JSON en AppData.

## Ejecución

Instala las dependencias del proyecto:

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Datos persistentes

En Windows, la configuración y la base de datos viven en:

```text
%APPDATA%\DesktopKioskCenter\
```

- `kiosks.json`: equipos, host/IP y puerto.
- `desktopkioskcenter.sqlite3`: alumnos internos, usuarios externos/público general y logs de peticiones/accesos.

La nueva versión importa, en su primer inicio, los registros heredados de `internal_students.json` y `external_users.json` si existen junto al programa. Los archivos antiguos no se eliminan automáticamente.

La estructura de tablas, la migración, las consultas de ejemplo y las instrucciones de mantenimiento están documentadas en [docs/DATABASE.md](docs/DATABASE.md). El acceso a SQLite se encuentra centralizado en `database.py`; los módulos `tabs/*/build.py` presentan widgets y los módulos `tabs/*/backend.py` conectan la interfaz con la base de datos.

## Pestañas

- **Equipos**: administra kioscos y los consulta cada pocos segundos.
- **Alumnos Internos Registrados**: guarda nombres, apellidos, facultad y expediente.
- **Usuarios Externos Registrados**: guarda nombres, apellidos, email, tipo de usuario y, cuando corresponda, universidad.
- **Logs de peticiones**: consulta solicitudes REST recibidas y permite contar totales por tipo y resultado.
- **Logs de accesos**: consulta accesos permitidos y permite contar totales por tipo de usuario y equipo.

## API REST

- `POST /api/v1/auth-client-pc/login`
- `POST /api/v1/users/register/alumno`
- `POST /api/v1/users/register/externo`

La API se inicia junto con la interfaz, por defecto en el puerto TCP 8080. El puerto se puede cambiar con `DESKTOPKIOSKCENTER_API_PORT`. Consulta [docs/API.md](docs/API.md) para ejemplos.

## Seguridad y alcance

El token común de los clientes sigue siendo `UAQinformatizacion7085`. Al tratarse de un valor compartido e incluido en los ejecutables, no debe considerarse un secreto fuerte; limita el acceso al puerto del cliente mediante el firewall y una red administrativa autorizada.

La API REST ya se ejecuta junto con la interfaz. El endpoint de inicio de sesión comprueba el registro, pero todavía no verifica contraseñas: el contrato de registro no incluye credenciales. Consulta [docs/API.md](docs/API.md) antes de habilitarla en una red compartida.
