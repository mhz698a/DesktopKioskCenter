# Manual de usuario — DesktopKioskCenter
**Versión:** 1.0  
**Fecha:** 25 de noviembre de 2026  
**Público:** operadores y administradores del centro de cómputo.

## 1. Propósito del programa
DesktopKioskCenter es la aplicación de administración central. Desde ella se registran los equipos DesktopKiosk, se controlan sus estados, se administran los usuarios que pueden utilizar el servicio y se consultan los registros de actividad y los reportes estadísticos.

El centro también proporciona la API local que utilizan los kioscos. Por ello, debe permanecer ejecutándose y tener conectividad de red con las computadoras administradas.

## 2. Pantalla principal
En la parte superior se muestra el nombre del panel, la hora, la fecha y la dirección IP detectada para el servidor central. La información se organiza en siete pestañas:

| Pestaña | Función |
|---|---|
| Equipos | Inventario, estado y control remoto de los kioscos. |
| Alumnos Internos Registrados | Alta y mantenimiento de alumnos internos. |
| Docentes y administrativos registrados | Alta y mantenimiento de personal universitario. |
| Usuarios Externos Registrados | Alta y mantenimiento de usuarios externos y público en general. |
| Logs de peticiones | Historial de solicitudes recibidas por la API. |
| Logs de accesos | Historial de accesos permitidos. |
| Estadísticas | Consultas agregadas y exportación de reportes. |

Las tablas se actualizan periódicamente. Al cambiar de pestaña, el centro vuelve a consultar los datos pertinentes para mostrar la información reciente.

## 3. Administrar equipos
### 3.1 Registrar un equipo
Abre la pestaña «Equipos». Para dar de alta una computadora:
1. Pulsa «Agregar Equipo».
2. Escribe un nombre que permita reconocer la ubicación o número físico de la computadora.
3. Escribe la dirección IP del equipo cliente.
4. Confirma el registro.

El puerto del kiosco se muestra como solo lectura y utiliza el valor configurado por la aplicación (7085). No registres dos equipos con el mismo nombre o dirección IP.

### 3.2 Registrar varios equipos
Pulsa «Agregar varios equipos» e indica:
- **Rango de equipos:** número inicial y final.
- **Nombre base:** prefijo al que se agregará el número. Por ejemplo, «PC #» con un rango de 1 a 15 produce PC #1 hasta PC #15.
- **IP Base:** los primeros tres octetos de la red, terminados en punto o guion bajo. Por ejemplo, 192.168.100._ con el rango 1 a 15 genera direcciones de 192.168.100.1 a 192.168.100.15.

Antes de confirmar, revisa el rango y que las IP pertenezcan realmente a la red donde están conectados los kioscos. El programa rechaza nombres o direcciones duplicadas.

### 3.3 Consultar el estado
La tabla presenta nombre del equipo, dirección IP, estado y tiempo de uso. Los estados son:
- **Disponible:** el kiosco está bloqueado y esperando un usuario.
- **En uso:** existe una sesión desbloqueada.
- **Sin conexión:** el centro dejó de recibir los reportes periódicos del cliente durante aproximadamente cuatro segundos.
- **Error:** el estado no pudo determinarse correctamente.

El cliente envía un reporte de estado aproximadamente cada segundo. «Sin conexión» no significa necesariamente que la computadora esté apagada: también puede deberse a un problema de red, al cierre del cliente o a una IP incorrecta.

### 3.4 Editar un equipo
Selecciona una fila de la tabla. El panel derecho habilita los campos «Nombre del Equipo» e «IP del Cliente». Modifica los datos y pulsa «Guardar cambios». «Revertir cambios» descarta la edición que todavía no se haya guardado.

El puerto y el estado son campos de solo lectura. Si cambió la dirección IP real de un equipo, actualiza aquí la dirección del cliente y verifica después la comunicación.

### 3.5 Acciones sobre un equipo
Selecciona primero el equipo que recibirá la orden. El panel lateral incluye:
- **Bloquear:** devuelve el kiosco a la pantalla de acceso.
- **Desbloquear:** libera el kiosco sin realizar el inicio de sesión habitual.
- **Cerrar Kiosko:** finaliza el proceso DesktopKiosk. El equipo dejará de reportar estado hasta que el cliente vuelva a ejecutarse.
- **Apagar PC:** solicita el apagado de Windows.
- **Reiniciar PC:** solicita el reinicio de Windows.
- **Enviar IP del servidor central a esta PC:** actualiza en el kiosco la dirección del servidor al que debe reportar su estado y enviar solicitudes.
- **Eliminar:** retira el equipo de la lista administrada.

Las acciones de cerrar, apagar, reiniciar y eliminar deben utilizarse solo cuando corresponda. Revisa el nombre y la IP del equipo seleccionado antes de ejecutarlas.

### 3.6 Acciones generales
En la barra superior se encuentran «Enviar IP del servidor central a todas las PCs», «Borrar todas las PCs», «Apagar todos los Equipos» y «Reiniciar todos los equipos». Son operaciones que afectan a varios equipos; confirma que el alcance sea correcto antes de aceptarlas.

**Importante sobre la IP:** enviar la IP del servidor central no cambia la dirección IP de Windows ni la configuración del adaptador de red del kiosco. Solo comunica al cliente cuál es la dirección del centro al que debe conectarse.

### 3.7 Credencial del administrador del kiosco
La acción «Credencial del administrador» muestra las credenciales locales utilizadas para abrir el menú administrativo del cliente. Son datos sensibles: consulta esta opción únicamente cuando sea necesario y no distribuyas sus valores a usuarios comunes.

## 4. Administrar alumnos internos
En «Alumnos Internos Registrados», pulsa «Agregar Alumno» y completa los campos:
- Nombres y apellidos.
- Correo electrónico.
- Facultad.
- Expediente.

El expediente debe contener números. El correo debe ser válido y no puede estar duplicado entre los registros del sistema.

Para editar un registro, selecciónalo en la tabla. Modifica los campos del panel derecho y pulsa «Guardar Cambios». «Revertir Cambios» recupera los datos guardados. «Eliminar Usuario» solicita confirmación antes de borrar el registro.

El catálogo de facultades se administra desde «Administrar facultades»; no es necesario editar el código del programa para agregar una facultad.

## 5. Administrar docentes y administrativos
En «Docentes y administrativos registrados», pulsa «Agregar personal». Selecciona el tipo «Docente» o «Administrativo» y captura:
- Nombres y apellidos.
- Correo electrónico.
- Facultad o unidad de adscripción.
- Número de empleado.

El número de empleado debe ser numérico y sirve como identificador institucional para el acceso, de forma equivalente al expediente de un alumno. El correo y el número de empleado deben ser únicos conforme a las validaciones del sistema.

La edición, guardado, reversión y eliminación se realizan desde el panel derecho. El catálogo de facultades es compartido con los alumnos internos.

## 6. Administrar usuarios externos
En «Usuarios Externos Registrados», pulsa «Agregar Usuario». Completa nombres, apellidos, correo electrónico y tipo de usuario. El campo de universidad se habilita únicamente cuando la regla del tipo seleccionado así lo requiere.

El catálogo inicial incluye:
- **Estudiante Externo:** requiere universidad.
- **Trabajador Interno:** no requiere universidad.
- **Público en general:** no requiere universidad.

Se pueden crear otros tipos personalizados y decidir para cada uno si debe solicitarse una universidad. Al guardar o editar, el centro valida que el tipo exista en el catálogo y que se cumpla su requisito de universidad.

Selecciona un usuario para editarlo, guardar cambios, revertir la edición o eliminarlo. Un correo electrónico no puede repetirse en el conjunto de usuarios.

## 7. Mantener los catálogos
### 7.1 Facultades
Desde la pestaña de alumnos o de docentes y administrativos, pulsa «Administrar facultades». En el diálogo puedes:
1. Escribir un nombre nuevo y pulsar «Agregar».
2. Seleccionar una facultad existente, modificar su nombre y pulsar «Renombrar».
3. Seleccionar una facultad y pulsar «Eliminar».

El catálogo se comparte entre alumnos, docentes y administrativos. Al renombrar una facultad, el cambio se refleja también en los registros e historial asociado. El sistema impide eliminar una facultad que todavía está en uso.

### 7.2 Tipos de usuario externo y universidades
Desde «Usuarios Externos Registrados», pulsa «Administrar tipos y universidades». El diálogo tiene dos secciones:
- **Tipos de usuario:** agrega un tipo, selecciona si requiere universidad, cambia sus propiedades o elimínalo cuando no esté en uso.
- **Universidades:** agrega una institución, renombra una existente o elimínala cuando no esté en uso.

Para modificar un tipo, selecciónalo en la lista, cambia el nombre o la casilla «Este tipo de usuario requiere seleccionar una universidad» y pulsa «Guardar cambios». El cambio de nombre y la regla se aplican juntos.

El sistema protege los registros históricos: no permite eliminar tipos o universidades que estén asociados a usuarios o accesos. Los cambios del catálogo se guardan en la base de datos de AppData y los kioscos consultan las opciones actualizadas al abrir el formulario de usuarios externos. No es necesario reinstalar cada kiosco para incorporar una nueva opción.

## 8. Asignar una sesión desde el centro
El panel del usuario incluye la sección «Equipo a entregar» y el botón «Desbloquear para este usuario». Esta función permite iniciar una sesión en un kiosco a nombre del usuario seleccionado, sin que tenga que capturar sus datos en ese equipo.

Procedimiento:
1. Abre la pestaña del tipo de usuario correspondiente.
2. Selecciona el registro correcto en la tabla.
3. En «Equipo a entregar», selecciona el kiosco de destino.
4. Pulsa «Desbloquear para este usuario».
5. Comprueba el nombre del equipo y de la persona en la confirmación.
6. Confirma únicamente si los datos son correctos.

La asignación está disponible para alumnos internos, docentes, administrativos y público en general. La operación queda registrada como asignación administrativa en el historial de accesos. No selecciones a una persona distinta de quien utilizará el equipo.

## 9. Consultar los registros
### 9.1 Logs de peticiones
Esta pestaña muestra las solicitudes que llegan al servidor central. Incluye fecha y hora, equipo, IP cliente, identificador, tipo de usuario, acción, resultado y mensaje. Pulsa «Contar Totales» para consultar los conteos agrupados por tipo de solicitud y resultado.

Los logs de peticiones sirven para investigar solicitudes fallidas, datos incompletos, identificadores no registrados o problemas de comunicación.

### 9.2 Logs de accesos
Esta pestaña muestra accesos permitidos. Incluye fecha y hora, equipo, nombres y apellidos, expediente o número de empleado, facultad, universidad externa y tipo de usuario. «Contar totales» permite consultar los acumulados disponibles.

Un registro de acceso representa un acceso autorizado y no es equivalente a cualquier petición recibida. Para investigar un intento rechazado, revisa también «Logs de peticiones».

## 10. Generar estadísticas y exportar PDF
Abre «Estadísticas». Elige el periodo con los campos «Desde» y «Hasta» y selecciona el criterio de agrupación de la tabla: por día, semana o mes. Después pulsa «Generar reporte».

El reporte presenta el total de accesos y una tabla agrupada por periodo y procedencia. A la derecha se muestran las gráficas:
- **Procedencia General:** distribución general de accesos y universidades.
- **Procedencia Facultades:** distribución de alumnos internos por facultad.

Las listas de universidades o facultades sin accesos en el rango seleccionado ayudan a identificar categorías que no tuvieron actividad durante ese periodo.

Para generar un documento, pulsa «Exportar PDF». En el diálogo:
1. Selecciona uno o varios agrupamientos: por día, semana o mes.
2. Elige tamaño de papel Carta o A4.
3. Define la ruta y el nombre del archivo.
4. Deja activada o desactiva «Abrir el PDF al terminar la exportación», según necesites.
5. Pulsa «Exportar PDF».

El botón CSV puede estar deshabilitado en la versión actual. La exportación principal disponible en esta interfaz es PDF.

## 11. Datos y respaldos
Los datos persistentes de DesktopKioskCenter se guardan en el perfil del usuario de Windows:

**Carpeta:** %APPDATA%\DesktopKioskCenter\

- **kiosks.json:** configuración de los equipos, incluidos nombre, host/IP y puerto.
- **desktopkioskcenter.sqlite3:** usuarios, facultades, tipos externos, universidades, logs y registros necesarios para los reportes.

Realiza copias de seguridad de ambos archivos con la aplicación cerrada. Conserva los respaldos en una ubicación institucional protegida y verifica que puedan recuperarse. No edites directamente la base SQLite mientras el centro esté en ejecución.

## 12. Diagnóstico básico
| Problema | Comprobación inicial |
|---|---|
| Un equipo aparece «Sin conexión» | Verifica que DesktopKiosk esté ejecutándose, que la IP sea correcta y que exista comunicación de red con el puerto 7085. |
| El kiosco no conoce el servidor central | Selecciona el equipo y usa «Enviar IP del servidor central a esta PC». Después verifica que vuelva a reportar estado. |
| Un usuario no puede iniciar sesión | Comprueba que el registro exista, que el identificador corresponda al perfil y que no haya datos duplicados o incompletos. |
| No aparece una facultad o universidad | Revisa el catálogo desde su diálogo de administración y confirma que el cambio quedó guardado. |
| No se puede eliminar un elemento del catálogo | Puede estar asociado a usuarios o al historial. Revisa los registros antes de intentar retirar el elemento. |
| No se genera el reporte | Confirma que el rango de fechas sea válido y que existan registros o categorías para el periodo seleccionado. |

Si el problema continúa, registra el nombre del kiosco, IP, hora aproximada y mensaje mostrado. Revisa «Logs de peticiones» y «Logs de accesos» antes de realizar cambios adicionales.

## 13. Recomendaciones operativas
- Verifica siempre el equipo y el usuario seleccionados antes de ejecutar acciones remotas.
- Utiliza las operaciones masivas solo después de revisar el alcance.
- Mantén actualizado el inventario de equipos y los catálogos institucionales.
- Protege las credenciales administrativas y los respaldos de la base de datos.
- Revisa los logs cuando un usuario reporte problemas de acceso.
- No elimines equipos ni elementos de catálogo sin comprobar primero si siguen en uso.