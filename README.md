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
- `desktopkioskcenter.sqlite3`: alumnos internos, usuarios externos/público general e inicios recibidos.

La nueva versión importa, en su primer inicio, los registros heredados de `internal_students.json` y `external_users.json` si existen junto al programa. Los archivos antiguos no se eliminan automáticamente.

La estructura de tablas, la migración, las consultas de ejemplo y las instrucciones de mantenimiento están documentadas en [docs/DATABASE.md](docs/DATABASE.md). El acceso a SQLite se encuentra centralizado en `database.py`; los módulos `tabs/*/build.py` presentan widgets y los módulos `tabs/*/backend.py` conectan la interfaz con la base de datos.

## Pestañas

- **Equipos**: administra kioscos y los consulta cada pocos segundos.
- **Alumnos Internos Registrados**: guarda nombres, apellidos, facultad y expediente.
- **Usuarios Externos Registrados**: guarda nombre, apellidos, tipo de usuario y, cuando corresponda, universidad.
- **Inicios Recibidos**: consulta los eventos guardados en SQLite y permite contar totales por tipo y resultado. La tabla recibe eventos cuando un backend de autenticación invoque `Database.record_received_login(...)`.

## Seguridad y alcance

El token común de los clientes sigue siendo `UAQinformatizacion7085`. Al tratarse de un valor compartido e incluido en los ejecutables, no debe considerarse un secreto fuerte; limita el acceso al puerto del cliente mediante el firewall y una red administrativa autorizada.

La integración del backend central de autenticación con DesktopKiosk se realizará como una fase separada.
