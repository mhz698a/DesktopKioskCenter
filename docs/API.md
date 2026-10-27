# API REST de DesktopKioskCenter

## Ejecución

El servidor REST se inicia junto con la aplicación. Por defecto escucha en `0.0.0.0:7085`; configura `DESKTOPKIOSKCENTER_API_HOST` o `DESKTOPKIOSKCENTER_API_PORT` para cambiarlo.

Los clientes envían un heartbeat cada segundo a `POST /api/v1/health`:

```http
POST /api/v1/health
Content-Type: application/json
X-Kiosk-Name: PC-Recepcion

{
  "action": "heartbeat",
  "data": {
    "status": 2,
    "time_string": "00:00:01"
  }
}
```

`data.status` es un entero del catálogo SQLite: `0 = Sin conexión`, `1 = Disponible`, `2 = En uso`, `3 = Inactividad`. El cliente solo puede reportar `1`, `2` o `3`; el servidor asigna el estado `0` cuando deja de recibir heartbeats durante 4 segundos.

La IP del cliente no se envía en el JSON. El servidor usa la IP remota de la conexión HTTP para actualizar el estado de ese equipo. Cada heartbeat actualiza el registro de `kiosk_heartbeats`, incluido el estado, `time_string` y la última hora de recepción. Un monitor en segundo plano marca los heartbeats vencidos como `Sin conexión`, sin esperar otra petición.

Todas las rutas POST reciben JSON. Las respuestas de las rutas funcionales contienen `unlocked` y `message`.

## Inicio de sesión — `POST /api/v1/auth-client-pc/login`

```json
{
  "action": "unlock_login",
  "data": {"usuario": "123456", "contrasena": ".123456"}
}
```

El campo `data.usuario` (o `data.identificador`) debe contener el correo electrónico del usuario o, para alumnos internos, el expediente. El servidor busca primero por email en todas las categorías de usuario, sin distinguir mayúsculas y minúsculas, y después por expediente. Los nombres no son identificadores de acceso. Si no existe, responde HTTP 401. Si existe, responde HTTP 200 con `unlocked: true`.

**Limitación importante:** los payloads de registro de esta especificación no contienen contraseña y SQLite no almacena credenciales. Actualmente la ruta comprueba que el usuario esté registrado y exige que el campo `contrasena` esté presente, pero no verifica que su valor sea correcto. Para utilizar el endpoint como autenticación segura, se necesita definir cómo registrar/verificar credenciales y almacenar hashes de contraseña. La contraseña nunca se incluye en logs.

## Registro de alumno — `POST /api/v1/users/register/alumno`

```json
{
  "action": "registro_alumno",
  "data": {
    "nombres": "Example Example",
    "apellidos": "Example Prueba",
    "email": "alumno@example.com",
    "facultad": "Facultad de Filosofía",
    "expediente": "123456"
  }
}
```

- Correo electrónico obligatorio, válido y único entre alumnos internos y usuarios externos; los duplicados devuelven HTTP 409.
- Expediente duplicado: HTTP 409, `unlocked: false`.
- Registro nuevo: HTTP 201, `unlocked: true` y `Registro de alumno completado con éxito.`.
- Nombres y apellidos admiten letras y espacios; expediente solo dígitos.

## Registro externo — `POST /api/v1/users/register/externo`

Estudiante externo:

```json
{
  "action": "registro_externo",
  "data": {
    "nombres": "Ejemplo Example",
    "apellidos": "Prueba Testing",
    "email": "estudiante@example.com",
    "tipo-usuario": "estudiante",
    "universidad-ext": "Universidad Tecnológica de Querétaro (UTEQ)"
  }
}
```

Público en general:

```json
{
  "action": "registro_externo",
  "data": {
    "nombres": "Ejemplo",
    "apellidos": "Prueba",
    "email": "emailtest@example.com",
    "tipo-usuario": "Público en general"
  }
}
```

El campo `tipo-usuario` debe indicar el tipo real de usuario: `estudiante`/`Estudiante Externo`, `Trabajador Interno` o `Público en general`. **Email es obligatorio para todos los tipos de usuario** (alumnos internos, estudiantes externos, trabajadores internos y público en general), debe tener un formato válido y no puede estar registrado previamente en ninguna de las tablas de usuarios. La universidad es obligatoria para estudiantes externos y no aplica a trabajadores internos ni público en general.

- Registro duplicado: HTTP 409, `unlocked: false` y el mensaje indicado.
- Registro nuevo: HTTP 201, `unlocked: true` y `Registro de usuario completado con éxito.`.

## Logs

Las peticiones recibidas se guardan en `received_logins`, sin registrar contraseñas. Los accesos y registros permitidos se guardan en `access_logs`. La cabecera opcional `X-Kiosk-Name` identifica el kiosco en los logs; de lo contrario se usa `Cliente API`.

Las solicitudes con acción incorrecta o campos inválidos reciben HTTP 400. El servicio escucha en todas las interfaces por defecto; restringe el puerto con el firewall de Windows a las redes de clientes autorizados.
