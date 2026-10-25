# Persistencia local de DesktopKioskCenter

## Ubicación de los datos

En Windows, los datos persistentes se guardan en:

`%APPDATA%\DesktopKioskCenter`

En esa carpeta se encuentran:

- `kiosks.json`: configuración de los equipos administrados.
- `desktopkioskcenter.sqlite3`: base de datos SQLite de alumnos, usuarios y eventos recibidos.

El código de la aplicación y sus estilos siguen en el directorio de instalación. En otros sistemas, la aplicación respeta `XDG_DATA_HOME` o utiliza `~/.local/share/DesktopKioskCenter`.

## Migración desde versiones anteriores

En el primer inicio de la nueva versión:

1. Si el archivo de AppData `kiosks.json` no existe, se intenta copiar el que estaba junto al programa.
2. SQLite busca `internal_students.json` y `external_users.json` en el directorio de la versión anterior.
3. Si los encuentra, importa sus filas a las tablas correspondientes.
4. La tabla `schema_migrations` guarda el marcador `legacy_user_json_to_sqlite_v1`, para que la importación no se repita en cada arranque.
5. Los archivos JSON antiguos no se eliminan: quedan como respaldo. Las nuevas altas ya se escriben en SQLite.

Si una fila de alumno tiene un expediente que ya existe, la restricción UNIQUE impide duplicarla. Las filas no válidas se omiten y se registran en el log de Python.

## Esquema

### `internal_students`

| Campo | Uso |
|---|---|
| `id` | Clave primaria autoincremental; se muestra como índice en la tabla |
| `nombres`, `apellidos` | Nombre del alumno |
| `facultad` | Facultad elegida del catálogo UAQ |
| `expediente` | Expediente numérico, único |
| `created_at` | Fecha de creación local |

### `external_users`

Contiene `id`, `nombres`, `apellidos`, `tipo_usuario`, `universidad` y `created_at`. El tipo de usuario determina si corresponde guardar una universidad. Para `Trabajador Interno` y `Público en general`, el backend limpia ese campo.

### `received_logins`

Almacena un evento por solicitud que procese el futuro backend central. Incluye fecha y hora, equipo, IP cliente, identificador, tipo de usuario, acción, resultado y mensaje. La pestaña **Inicios Recibidos** lee esta tabla y **Contar Totales** hace conteos SQL por total, tipo de usuario y resultado.

La tabla puede estar vacía hasta que un backend de autenticación invoque `Database.record_received_login(...)`. La interfaz no inventa eventos de prueba.

### `schema_migrations`

Registra migraciones de datos ya ejecutadas. Esto hace explícito y revisable el proceso de actualización de esquema.

## Cómo funciona el módulo

Todo el acceso SQL está centralizado en el archivo raíz `database.py`:

- `Database.initialize()`: crea tablas e índices y ejecuta la migración de JSON heredado.
- `Database.connection()`: abre una conexión por operación, activa claves foráneas y timeout de espera, confirma al terminar o revierte si hay una excepción, y siempre cierra la conexión.
- `list_...`: lee filas y las convierte en diccionarios para la interfaz.
- `add_...`: inserta datos mediante parámetros SQL (`?`), no concatenando texto de los formularios.
- `record_received_login(...)`: permite que la futura API central registre una solicitud recibida.
- `count_received_logins()`: hace el conteo directamente en SQLite.

La interfaz usa módulos separados: `tabs/<pestaña>/build.py` construye widgets y emite señales; `tabs/<pestaña>/backend.py` conecta esas señales con la clase `Database`. Así se pueden probar las consultas sin iniciar la interfaz gráfica.

## Consultas de mantenimiento

La base de datos se puede estudiar con cualquier visor SQLite. Estas consultas muestran el tamaño de cada tabla:

```sql
SELECT 'internal_students' AS tabla, COUNT(*) AS total FROM internal_students
UNION ALL
SELECT 'external_users', COUNT(*) FROM external_users
UNION ALL
SELECT 'received_logins', COUNT(*) FROM received_logins;
```

Ver los últimos eventos recibidos:

```sql
SELECT received_at, kiosk_name, client_ip, identifier, user_type, action, result, message
FROM received_logins
ORDER BY id DESC
LIMIT 50;
```

La librería `sqlite3` forma parte de la biblioteca estándar de Python; no requiere instalar una dependencia adicional.
