# Persistencia local de DesktopKioskCenter

## Ubicación de los datos

En Windows, los datos persistentes se guardan en:

`%APPDATA%\DesktopKioskCenter`

En esa carpeta se encuentran:

- `kiosks.json`: configuración de los equipos administrados.
- `desktopkioskcenter.sqlite3`: base de datos SQLite de alumnos, usuarios, logs de peticiones y logs de accesos.

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

Contiene `id`, `nombres`, `apellidos`, `email`, `tipo_usuario`, `universidad` y `created_at`. Email es obligatorio y único para todos los nuevos usuarios externos, trabajadores internos y público en general. Debe tener formato válido y la comparación de unicidad no distingue mayúsculas. El tipo de usuario determina si corresponde guardar una universidad. Para `Trabajador Interno` y `Público en general`, el backend limpia ese campo.

Al abrir una base existente, `Database.initialize()` añade `email TEXT NOT NULL DEFAULT ''` si la columna aún no existe, por lo que los registros anteriores conservan sus datos y reciben email vacío. Los registros heredados deben completarse con un email válido desde el panel de edición antes de poder guardarlos de nuevo.

### `received_logins` — Logs de peticiones

Almacena un evento por solicitud que procese el futuro backend central. Incluye fecha y hora, equipo, IP cliente, identificador, tipo de usuario, acción, resultado y mensaje. La pestaña **Logs de peticiones** lee esta tabla y **Contar Totales** hace conteos SQL por total, tipo de usuario y resultado.

La tabla puede estar vacía hasta que un backend de autenticación invoque `Database.record_received_login(...)`. La interfaz no inventa eventos de prueba.

### `access_logs` — Logs de accesos

Guarda un evento de acceso con fecha y hora, equipo, nombres, apellidos, expediente, facultad, universidad externa y tipo de usuario. La pestaña **Logs de accesos** muestra esas nueve columnas y su opción **Contar totales** consulta el total, los subtotales por tipo de usuario y los subtotales por equipo. El método `Database.record_access_log(...)` permite que el servicio de autenticación inserte un acceso procesado. La tabla permanece vacía hasta que esa integración invoque el método.

Las pestañas **Alumnos Internos Registrados** y **Usuarios Externos Registrados** disponen de un panel lateral para editar el registro seleccionado. Los cambios se guardan mediante los métodos `update_...`; las acciones de eliminación usan `delete_...` y solicitan confirmación. **Revertir Cambios** restaura los valores de la selección actual.

### `kiosk_status_codes` — Catálogo de estados

Es la tabla de referencia de los estados de los equipos. `status_code` es la clave y `label` es la etiqueta que se muestra en la UI. La inicialización siembra los cuatro valores predeterminados con `INSERT OR IGNORE`, por lo que las etiquetas se pueden mantener en SQLite sin hardcodearlas en la interfaz.

| Código | Etiqueta predeterminada |
|---:|---|
| 0 | Sin conexión |
| 1 | Disponible |
| 2 | En uso |
| 3 | Inactividad |

### `kiosk_heartbeats` — Último estado recibido por equipo

Cada IP de origen tiene un registro con clave primaria `client_ip`, la referencia `status_code` al catálogo, `time_string` y la marca de tiempo `last_seen_at`. Cada petición heartbeat hace un upsert de la fila correspondiente. El servidor utiliza `request.remote_addr`; no espera la IP dentro del JSON. Cuando pasan 4 segundos sin un heartbeat, un monitor del servicio cambia el código a 0 sin depender de nuevas peticiones.

### `schema_migrations`

Registra migraciones de datos ya ejecutadas. Esto hace explícito y revisable el proceso de actualización de esquema.

## Cómo funciona el módulo

Todo el acceso SQL está centralizado en el archivo raíz `database.py`:

- `Database.initialize()`: crea tablas e índices y ejecuta la migración de JSON heredado.
- `Database.connection()`: abre una conexión por operación, activa claves foráneas y timeout de espera, confirma al terminar o revierte si hay una excepción, y siempre cierra la conexión.
- `list_...`: lee filas y las convierte en diccionarios para la interfaz.
- `add_...`: inserta datos mediante parámetros SQL (`?`), no concatenando texto de los formularios.
- `update_...` y `delete_...`: guardan o eliminan los registros seleccionados en las tablas de alumnos y usuarios.
- `record_access_log(...)`: añade un evento de acceso; `count_access_logs()` calcula los totales directamente en SQLite.
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
SELECT 'received_logins', COUNT(*) FROM received_logins
UNION ALL
SELECT 'kiosk_status_codes', COUNT(*) FROM kiosk_status_codes
UNION ALL
SELECT 'kiosk_heartbeats', COUNT(*) FROM kiosk_heartbeats;
```

Ver los últimos eventos recibidos:

```sql
SELECT received_at, kiosk_name, client_ip, identifier, user_type, action, result, message
FROM received_logins
ORDER BY id DESC
LIMIT 50;
```

La librería `sqlite3` forma parte de la biblioteca estándar de Python; no requiere instalar una dependencia adicional.
