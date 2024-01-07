# Configuración de la máquina para producción

Estas instrucciones están pensadas para configurar por primera vez la máquina productiva. Solo debería ser necesario seguir estas instrucciones para configurar una máquina nueva.

## Instrucciones iniciales

### General

1. Actualizar paquetes de la máquina (`dnf update`).
2. Instalar git.
3. Clonar el **repositorio de producción** del proyecto nuevo planner (`git clone`).
4. Desplegar por primera vez el proyecto usando el playbook de _ansible_ de forma manual (`ansible-playbook playbook.yml -e "playbook_run_mode=manual"`).
5. Permitir actualizaciones recurrentes: copiar el archivo `update.sh` fuera del proyecto (`cp`), darle permisos de ejecución (`chmod`) y crear un _cron job_ que lo ejecute recurrentemente.

### Detalles

1. Actualizar paquetes de la máquina. Para el caso de Rocky Linux 9 se puede usar "`sudo dnf check-update`" y "`sudo dnf update`".
2. Instalar git. Para Rocky Linux 9 se puede usar "`sudo dnf install git`". En la siguiente sección [Informacion de los archivos](informacion-de-los-archivos) se muestra como _ansible_ instalará el resto de dependencias necesarias, tales como Docker.
3. Clonar el **repositorio de producción** del proyecto nuevo planner usando "`git clone`". Este repositorio se encuentra en Github controlado exclusivamente por la **Subdirección de Desarrollo** (más detalles en la sección [Flujo 2: Actualizaciones recurrentes](flujo-2:-actualizaciones-recurrentes)). Se recomienda instalar en la carpeta `/opt` de la máquina. Los comandos finales deberían quedar como: "`cd /opt`" y luego "`sudo git clone https://github.com/<nombre-organizacion>/planner.git`".
4. Para desplegar por primera vez el proyecto de forma manual:
- primero es necesario instalar _ansible_ con "`sudo dnf install epel-release`" y "`sudo dnf install ansible`".
- Luego, se ejecutan las instrucciones del playbook de forma manual, entrando a la carpeta infra del proyecto con "`cd /opt/planner/infra`", y usando el comando "`ansible-playbook playbook.yml -e "playbook_run_mode=manual"`". Se va a solicitar al usuario ingresar algunos valores en la consola, para así configurar las variables de entorno en un nuevo archivo "`/opt/planner/backend/.env`", además de aplicar otras configuraciones a la máquina para ejecutar el proyecto de forma óptima.
- Finalmente, se van a construir e iniciar los contenedores de la aplicación de forma automática (esto podría tomar bastante tiempo, ya que está descargando por primera vez todas las dependencias necesarias para correr el proyecto). Va a aparecer un mensaje del estilo "TASK [Build and start containers] ************", solamente hay que esperar a que esté listo.
- Una vez que haya completado exitosamente el lanzamiento, se puede ver los logs de todos los contenedores con el comando "`sudo docker compose logs -f`" para verificar que no hayan ocurrido problemas inesperados.
5. Para permitir las actualizaciones recurrentes del proyecto, es necesario:
- primero copiar el archivo `update.sh` hacia una ubicación fuera del proyecto. Por ejemplo, *home* (`~`) del usuario con el comando "`sudo cp /opt/planner/infra/productive-deploy/update.sh ~`".
- Luego, darle permisos de ejecución al archivo usando el comando "`sudo chmod +x ~/update.sh`".
- Si todo va bien hasta ahora, se debería poder ejectuar "`sudo ~/update.sh`" sin problemas.
- Finalmente, se usa el comando "`crontab -e`" para definir un *cron job* que ejecute el archivo recurrentemente. Se recomienda una frecuencia no tan baja, para que las actualizaciones ocurran de forma más inmediata. Por ejemplo, cada media hora agregando la línea: "`*/30 * * * * sudo ~/update.sh`". De esta forma, hay un rango máximo de 30 minutos desde que se hizo el merge a main hasta que se ejecuta el deploy en la máquina.
- Para monitorear, se pueden revisar los últimos logs de *cron* con el siguiente comando "`tail -100 /var/log/cron`".
   Otra alternativa puede ser definir una recurrencia de todos los días a las 5AM con la línea: "`0 5 * * * sudo ~/update.sh`". La desventaja aquí es que si algo sale mal nadie estará supervisando.

   ❓ Aclaración: Es importante mencionar que la ejecución de este archivo no será demandante computacionalmente, ya que solamente tomará acciones si es que hubo algún cambio en el **repositorio de producción**. O sea, si el archivo se ejecuta cada 1 hora, pero el código del proyecto no cambia en 5 días, solamente se ejecutará el proceso de deploy una vez, luego de 5 días. El resto de las ejecuciones de este archivo no tendrán impacto debido a que el código no tuvo cambios.

   ❓ Aclaración: El archivo `update.sh` requiere permisos `sudo` para ser ejecutado, por lo que podría ser necesario utiliar la siguiente línea en caso de que haya una contraseña establecida en la máquina "`*/30 * * * * echo "contraseña_establecida" | sudo -S ~/update.sh`". Esto no es recomendable, ya que requiere dejar la contraseña escrita directamente en el *cron job* (muy inseguro). La opción recomendada es definir un usuario con permisos suficientes, y utilizarlo para ejecutar el archivo.

   ⚠️ Advertencia: Cuando se ejecuta exitosamente el proceso de deploy, el Planner estará caído por unos minutos, ya que se reinician los contenedores.

## Información de los archivos

- `install.md`: este archivo entrega las instrucciones necesarias para configurar por primera vez la máquina que será utilizada para correr el proyecto nuevo planner.
- `update.sh`: este archivo será ejecutado automáticamente, con un _cronjob_, para actualizar el código y desplegar los nuevos cambios. En particular, ejecuta el comando `git pull` para obtener los últimos cambios del repositorio de producción del proyecto nuevo planner, y luego corre el archivo `run_deploy.sh` solamente si git registró algún cambio nuevo en el repositorio.
- `run_deploy.sh`: finalmente, este archivo es ejecutado automáticamente por `update.sh` y lo que hace es levantar la última versión del proyecto. En particular, instala _ansible_ si no está instalado, y luego corre el playbook de _ansible_. En este caso, _ansible_ actúa como una interfaz para generar la instancia de deploy. Actualmente usamos _ansible_, pero en el futuro se puede ver la posibilidad de usar otro servicio.

## Flujos de despliegue a producción explicados en detalle

### Flujo 1: Despliegue inicial

1. El **Equipo de Plataformas** levanta una nueva máquina vacía para producción.
2. El **Equipo de Desarrollo del Nuevo Planner** le entrega los archivos `install.md` y `update.sh` a la **Subdirección de Desarrollo**. Estos archivos también se encontrarán en el repositorio del proyecto, bajo la ubicación `infra/productive-deploy`.
3. La **Subdirección de Desarrollo** accede a la máquina y sigue las instrucciones del archivo `install.md`.

### Flujo 2: Actualizaciones recurrentes

1. El **Equipo de Desarrollo** del Nuevo Planner y la comunidad UC generan solicitudes de cambios al código (_Pull Requests_) en el **repositorio de desarrollo** del proyecto Nuevo Planner. Este repositorio es público y se ubica en Github bajo la organización Open Source UC ([github.com/open-source-uc/planner](https://github.com/open-source-uc/planner/tree/main)).
2. El **Equipo de Desarrollo** del Nuevo Planner acepta una solicitud de cambio al código y agrega estos cambios a la rama principal (_Main_) del **repositorio de desarrollo**.
3. Luego, el **Equipo de Desarrollo** del Nuevo Planner genera una solicitud para agregar los cambios a la rama principal (_Main_) del **repositorio de producción**, desde la rama principal del **repositorio de desarrollo**. El **repositorio de producción** también es público en Github, pero se ubica bajo el control exclusivo de la **Subdirección de Desarrollo**. O sea, solamente la **Subdirección de Desarrollo** puede aprobar y realizar cambios al código del proyecto.
4. La **Subdirección de Desarrollo** revisa la solicitud, y puede aceptarla o solicitar cambios. Si solicita cambios, el **Equipo de Desarrollo** del Nuevo Planner deberá arreglar lo solicitado y volver a generar una solicitud para agregar los cambios.
5. Si la solicitud fue aceptada, los nuevos cambios de la rama principal del **repositorio de producción** se van a actualizar automáticamente en la máquina de producción. Esta actualización se genera a través del archivo `update.sh` que se ejecuta recurrentemente en la máquina de producción con un _cronjob_.
