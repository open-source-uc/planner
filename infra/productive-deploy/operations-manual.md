# Manual de Operaciones para el Planner

Este manual tiene como objetivo proporcionar una guía detallada para la gestión y mantenimiento del Planner. Se explican procedimientos para cambios de código, administración de contenedores Docker, respaldo de base de datos, y manejo de incidencias.

## Cambios de Código a través de GitHub

En las operaciones de la máquina productiva, existirán varias tareas que requieran modificar parte del código fuente del proyecto. Pero el código de la máquina se actualizará automáticamente con la última versión publicada en Github del proyecto Nuevo Planner, por lo que **es necesario hacer los cambios directamente en el repositorio de producción** y luego actualizar la máquina manualmente para **asegurarse de no perder ningún cambio**. Esto incluye cualquier cambio al código, tales como versión de paquetes utilizados, configuración de Docker, configuración del web server (Caddy), etc.

El flujo debe ser el siguiente:

1. Identificar el cambio que se quiere hacer (e.g. modificar la versión que se usa de una librería en el `package.json` del backend).
2. Ir al **repositorio de producción** ubicado en Github, hacer el cambio en una nueva rama de este, y generar la solicitud hacia la rama principal `main`.
3. Un vez que el cambio fue aprobado por la **Subdirección de Desarrollo** (la entidad de la universidad que está a cargo del código), la máquina será automáticamente actualizada luego de un plazo definido. Esta actualización ocurre de forma recurrente, a través de un _cronjob_ definido por la **Subdirección de Desarrollo** al levantar el proyecto por primera vez en la máquina.
4. (Opcional) Si es que el cambio es urgente, se puede forzar la actualización manual de la máquina ejecutando el archivo `update.sh`. De esta forma, no será necesario esperar al _cronjob_ recurrente para hacer efectivos los cambios. Más información en la sección [Forzar Actualizaciones Manualmente](#forzar-actualizaciones-manualmente).

⚠️ Advertencia: es muy importante seguir este flujo al querer hacer cambios en el código, ya que de lo contrario los cambios no "commiteados" en el repositorio de Github se van a borrar de la máquina durante la actualización recurrente.

❓ Aclaración: el "**repositorio de producción**" se refiere al repositorio ubicado en Github bajo el control exclusivo de la **Subdirección de Desarrollo**. No confundir con el repositorio **de desarrollo** controlado por la organización Open Source UC.

## Notas sobre el comportamiento de los contenedores

- Al reiniciar la máquina, los contenedores Docker se levantan automáticamente. Si ocurrió un problema, seguirán intentando levantarse hasta llegar a un limite de muchos intentos.

## Respaldo de Base de Datos

Para la base de datos, se utiliza un contenedor de Docker llamado "planner-db" que utiliza PostgreSQL. Actualmente, estamos usando la **versión 15** de la [imagen oficial de postgres](https://hub.docker.com/_/postgres) en Docker Hub.

Se puede ingresar a este contenedor con el comando `docker exec -it planner-db ash`. Desde aquí, existe acceso a herramientas pre-instaladas en la imagen de PostgreSQL, tales como `psql` y `pg_dump`.

Para generar y restaurar respaldos de la base de datos, se pueden utilizar ambos comandos de la siguiente manera:

1. Generar respaldo: `docker exec planner-db pg_dump -U [nombre_usuario] [nombre_base_de_datos] > [ruta_archivo_sql_output]`.

   Por ejemplo,

   > `docker exec planner-db pg_dump -U postgres postgres > /ruta/para/guardar/el/backup.sql`

2. Restaurar respaldo: `docker exec -i planner-db psql -U [nombre_usuario] -d [nombre_base_de_datos] < [ruta_archivo_sql_input]`.

   Por ejemplo,

   > `docker exec -i planner-db psql -U postgres -d postgres < /ruta/para/guardar/el/backup.sql`

## Algunos Comandos Útiles

- Acceso a un contenedor (_backend_, _frontend_, _bbdd_ y _redis_ respectivamente):

  > docker exec -it [planner-api | planner-web | planner-db | planner-redis] ash

- Revisar el estado de los contenedores

  > docker ps

- Detener todos los contenedores:

  > docker compose down

  💠 Nota: los comandos podrían variar ligeramente dependiendo del sistema operativo y versión de _Docker Compose_. En particular, podría ser necesario utilizar `docker-compose` en vez de `docker compose` y `sudo docker compose` en vez de `docker compose`.

- Levantar todos los contenedores de producción:

  > docker compose up planner -d --build

  💠 Nota: `planner` es el nombre del servicio web, del cual dependen los demás, por lo que se encienden automáticamente al encender este servicio.

- Reiniciar todos los contenedores:

  > docker compose restart

- Obtener logs de un contenedor:

  > docker logs [planner-api | planner-web | planner-db | planner-redis]

  - Variaciones útiles para gestionar logs

    - Ver los últimos N líneas de logs de un contenedor:

      > docker logs --tail N [planner-api | planner-web | planner-db | planner-redis]

    - Seguir los logs de un contenedor (streaming en tiempo real):

      > docker logs -f [planner-api | planner-web | planner-db | planner-redis]

    - Ver logs de un contenedor desde una fecha y hora específica:

      > docker logs --since YYYY-MM-DDTHH:MM:SS [planner-api | planner-web | planner-db | planner-redis]

    - Ver logs de un contenedor de los últimos X minutos:

      > docker logs --since Xm [planner-api | planner-web | planner-db | planner-redis]

    - Guardar los logs de un contenedor en un archivo:

      > docker logs [planner-api | planner-web | planner-db | planner-redis] > /ruta/al/archivo.log

## Actualización de la Plataforma

Para actualizar el servicio expuesto a internet y aplicar parches de seguridad.

### Actualización de Backend y Frontend

- **Backend (Python):**
  El archivo `pyproject.toml` contiene las versiones compatibles con el proyecto. Si es necesario instalar una versión específica de un paquete, se debe modificar la versión en este archivo.

  💠 Nota: Considera eliminar el archivo `poetry.lock` para actualizar automáticamente a las nuevas versiones.

- **Frontend (Node.js):**
  Se usa NPM para manejar dependencias. Si es necesario instalar una versión específica de un paquete, se debe modificar la versión en el archivo `package.json`.

  💠 Nota: Considera eliminar el archivo `package-lock.json` para actualizar automáticamente a las nuevas versiones.

⚠️ Advertencia: ambas modificaciones presentadas aquí significan cambios al código, por lo que deben ser "commiteadas" al **repositorio de producción** tal como se muestra en la primera sección de este documento.

### Renovación de Certificados

- La renovación de certificados es automática con el servidor web [Caddy](https://caddyserver.com/).
- En caso de problemas, primero revisar si es posible solucionarlo modificando la configuración de Caddy en el archivo `Caddyfile` ubicado en `frontend/conf/Caddyfile`.
- En emergencias, si lo anterior no funcionó entonces se puede revisar la carpeta que contiene los certificados para una probar un renovación manual. Estos se encuentran en un volumen Docker llamado `caddy_data`. Una forma de acceder a esta ubicación para encontrar los certificados almacenados es generar un contenedor temporal con el siguiente comando:
  > docker run --rm -it -v caddy_data:/data alpine

### Forzar Actualizaciones Manualmente

Tal como se mencionó al comienzo, hay un archivo llamado `update.sh` que está programado para ejecutarse recurrentemente con un _cron job_ en la máquina. En el flujo normal de actualizaciones, solamente debería ser necesario modificar el código de la rama principal _main_ en el **repositorio de producción** para hacer cambios al proyecto. Pero en el caso de una emergencia, es posible ejecutar manualmente el archivo `~/update.sh` para forzar una actualización inmediatamente, sin tener que esperar al _cron job_ recurrente. La ejecución de este archivo debería ser suficiente.

❓ Aclaración: El archivo `update.sh` se encuentra en una ubicación definida por la **Subdirección de Desarrollo**, que podría ser *home* del usuario asignado (`~`).

En caso de tener problemas con las actualizaciones recurrentes, se puede revisar el _cron job_ usando el siguiente comando:

> crontab -e

Además, el siguiente comando sirve para revisar los últimos logs de *cron*:

> tail -100 /var/log/cron

## Nuevas Incidencias

- Cualquier incidencia crítica que surja durante la puesta en marcha, y no se encuentre documentada en este manual, debe ser comunicada al **Equipo de Desarrollo** del proyecto Nuevo Planner.
- Para incidencias no críticas, siempre está la opción de generar un _issue_ en el [repositorio de desarrollo](https://github.com/open-source-uc/planner/issues) del proyecto.
