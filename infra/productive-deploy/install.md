# Configuración de la máquina para producción

Estas instrucciones están pensadas para configurar por primera vez la máquina productiva. Solo debería ser necesario seguir estas instrucciones para configurar una máquina nueva.

## Instrucciones iniciales

### General

1. Actualizar paquetes de la máquina (`dnf update`).
2. Instalar git.
3. Clonar el **repositorio de producción** del proyecto nuevo planner (`git clone`).
4. Correr la primera instancia de deploy usando el playbook de _ansible_ de forma manual.
5. Agregar a la máquina el archivo `update.sh`, dar permisos de ejecución con el comando `chmod` y crear _cronjob_ que lo ejecute recurrentemente.

### Detalles

1. Actualizar paquetes de la máquina. Para el caso de Rocky Linux se puede usar `sudo dnf check-update` y `sudo dnf update`.
2. Instalar git. En la siguiente sección [Informacion de los archivos](informacion-de-los-archivos) se muestra como _ansible_ instalará el resto de dependencias necesarias, tales como Docker.
3. Clonar el **repositorio de producción** del proyecto nuevo planner usando `git clone`. Este repositorio se encontrará en Github controlado exclusivamente por la **Subdirección de Desarrollo** (más detalles en la sección [Flujo 2: Actualizaciones recurrentes](flujo-2:-actualizaciones-recurrentes)). El comando debería quedar como: `git clone https://github.com/<nombre organizacion>/planner`.
4. Para correr la primera instancia de deploy de forma manual, primero es necesario instalar _ansible_ con "`sudo dnf install epel-release`" y "`sudo dnf install ansible`". Luego, usar el comando "`ansible-playbook playbook.yml -e "playbook_run_mode=manual"`". Esto va a solicitar algunos valores en la consola, para configurar el archivo `backend/.env`, además de aplicar otras configuraciones a la máquina para correr el proyecto de forma óptima. Finalmente, se van a construir e iniciar los contenedores de forma automática (esto podría tomar bastante tiempo, aunque parezca que se quedó pegado realmente solo está cargando).
5. Para permitir las actualizaciones recurrentes del proyecto, es necesario agregar a la maquina el archivo `update.sh`, luego darle permisos de ejecución con el comando `chmod +x update.sh`, y luego crear el _cronjob_ que lo ejecute recurrentemente con el comando `crontab -e`. Se recomienda una frecuencia no tan baja, para que las actualizaciones ocurran de forma más inmediata. Por ejemplo, cada media hora agregando la línea: "`*/30 * * * * /opt/planner/infra/productive-deploy/update.sh`". De esta forma, hay un rango máximo de 30 minutos desde que se hizo el merge a main hasta que se ejecuta el deploy en la máquina.
   Otra alternativa puede ser todos los días a las 5AM con la línea: "`0 5 * * * /opt/planner/infra/productive-deploy/update.sh`". La desventaja es que si algo sale mal nadie estará supervisando.

   ❓ Aclaración: Es importante mencionar que la ejecución de este archivo no será demandante computacionalmente, ya que solamente tomará acciones si es que hubo algún cambio en el **repositorio de producción**. O sea, si el archivo se ejecuta cada 3 horas, pero el código del proyecto no cambia en 5 días, solamente se ejecutará el proceso de deploy luego de 5 días. El resto de las ejecuciones de este archivo no tendrán impacto debido a que el código no tuvo cambios.

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
