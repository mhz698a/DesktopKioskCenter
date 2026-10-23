# DesktopKioskCenter — MVP

Gestor central en PyQt6 para administrar equipos que ejecutan un cliente Kiosk local basado en Flask.

## Componentes

- `client/kiosk_client.py`: cliente Kiosk. Expone:
  - `POST /api/kiosk/lock`
  - `POST /api/kiosk/unlock`
  - `POST /api/kiosk/close`
  - `GET /api/kiosk/status`
- `manager/main.py`: aplicación PyQt6 para administrar equipos.
- `manager/kiosks.json`: persistencia de equipos del MVP.
- Autenticación mediante `Authorization: Bearer <TOKEN>`.

## Instalación

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

## Ejecutar un Kiosk cliente

Windows:

```powershell
$env:DESKTOPKIOSK_API_TOKEN="cambia-este-token"
python client/kiosk_client.py
```

Linux/macOS:

```bash
export DESKTOPKIOSK_API_TOKEN="cambia-este-token"
python client/kiosk_client.py
```

Por defecto escucha en `0.0.0.0:7085`.

## Ejecutar el gestor

Windows:

```powershell
$env:DESKTOPKIOSK_API_TOKEN="cambia-este-token"
python manager/main.py
```

Linux/macOS:

```bash
export DESKTOPKIOSK_API_TOKEN="cambia-este-token"
python manager/main.py
```

El gestor también permite introducir un token diferente por equipo desde «Agregar equipo» o «Editar».

## Prueba manual de API

```bash
curl -X POST http://127.0.0.1:7085/api/kiosk/lock \
  -H "Authorization: Bearer cambia-este-token"
```

Estado:

```bash
curl http://127.0.0.1:7085/api/kiosk/status \
  -H "Authorization: Bearer cambia-este-token"
```

Desbloqueo:

```bash
curl -X POST http://127.0.0.1:7085/api/kiosk/unlock \
  -H "Authorization: Bearer cambia-este-token"
```

## Nota de seguridad

Este MVP implementa el bloqueo como una ventana de pantalla completa del propio Kiosk. No intenta saltarse la autenticación del sistema operativo para «desbloquear» Windows, Linux o macOS. Para un producto real, el acceso remoto debe ir sobre TLS/VPN o una red administrativa aislada, con tokens rotatorios y registro de auditoría.
