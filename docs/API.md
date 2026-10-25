# API REST de DesktopKioskCenter

## Ejecución

El servidor REST se inicia junto con la aplicación. Por defecto escucha en `0.0.0.0:7085`; configura `DESKTOPKIOSKCENTER_API_HOST` o `DESKTOPKIOSKCENTER_API_PORT` para cambiarlo.

```http
GET /api/v1/health
```

Todas las rutas POST reciben JSON. Las respuestas de las rutas funcionales contienen `unlocked` y `message`.

## Inicio de sesión — `POST /api/v1/auth-client-pc/login`

```json
{
  "action": "unlock_login",
  "data": {"usuario": "123456", "contrasena": ".123456"}
}
```

El campo `data.usuario` puede ser el expediente de un alumno interno o el email de un usuario externo. La búsqueda de email ignora mayúsculas/minúsculas. Si no existe, responde HTTP 401 con el mensaje solicitado. Si existe, responde HTTP 200 con `unlocked: true`.

**Limitación importante:** los payloads de registro de esta especificación no contienen contraseña y SQLite no almacena credenciales. Actualmente la ruta comprueba que el usuario esté registrado y exige que el campo `contrasena` esté presente, pero no verifica que su valor sea correcto. Para utilizar el endpoint como autenticación segura, se necesita definir cómo registrar/verificar credenciales y almacenar hashes de contraseña. La contraseña nunca se incluye en logs.

## Registro de alumno — `POST /api/v1/users/register/alumno`

```json
{
  "action": "registro_alumno",
  "data": {
    "nombres": "Example Example",
    "apellidos": "Example Prueba",
    "facultad": "Facultad de Filosofía",
    "expediente": "123456"
  }
}
```

- Expediente duplicado: HTTP 409, `unlocked: false` y el mensaje indicado.
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

El campo `tipo-usuario` debe indicar el tipo real de usuario: `estudiante`/`Estudiante Externo`, `Trabajador Interno` o `Público en general`. **Email es obligatorio para los tres tipos externos**, debe tener un formato válido y no puede estar registrado previamente. La universidad es obligatoria para estudiantes externos y no aplica a trabajadores internos ni público en general.

- Registro duplicado: HTTP 409, `unlocked: false` y el mensaje indicado.
- Registro nuevo: HTTP 201, `unlocked: true` y `Registro de usuario completado con éxito.`.

## Logs

Las peticiones recibidas se guardan en `received_logins`, sin registrar contraseñas. Los accesos y registros permitidos se guardan en `access_logs`. La cabecera opcional `X-Kiosk-Name` identifica el kiosco en los logs; de lo contrario se usa `Cliente API`.

Las solicitudes con acción incorrecta o campos inválidos reciben HTTP 400. El servicio escucha en todas las interfaces por defecto; restringe el puerto con el firewall de Windows a las redes de clientes autorizados.
