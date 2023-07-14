<h1 align="center">
  <br>
  <a href=# name="readme-top">Proyecto Planner</a>
</h1>

<p align="center">
     <!-- Badges Here -->
</p>

<p align="center">
  <a href="#descripción">Descripción</a> •
  <a href="#instalación-y-desarrollo">Instalación</a> •
  <a href="#mocks">Mocks</a> •
  <a href="#staging-server-y-producción">Staging y Producción</a> •
  <a href="#equipo">Equipo</a> •
  <a href="#licencia">Licencia</a>
</p>

<h4 align="center">
  <a href=# name="readme-top"><img src="./docs/img/demo_gif.gif" width="700px" alt="banner"></a>
</Es>

---

## Descripción

Este es el hogar para el desarrollo del nuevo Planner de Ingeniería UC, hecho por estudiantes para estudiantes.

Tras varios años en ideación, este proyecto se lanzó como [una propuesta conjunta](https://drive.google.com/file/d/1IxAJ8cCzDkayPwnju5kgc2oKc7g9fvwf/view) entre la Consejería Académica de Ingeniería y Open Source UC, con el propósito de reemplazar el [actual planner de Ingeniería](https://planner.ing.puc.cl/). La propuesta, tras ser aprobada por la Escuela de Ingeniería, dió comienzo al proyecto en modalidad de marcha blanca. A principios del 2023, y con un MVP listo, la Dirección de Pregrado oficialmente aprobó la continuación del desarrollo del proyecto.

## Instalación y desarrollo

El proyecto está configurado para ser desarrollado en [Visual Studio Code](https://code.visualstudio.com/) con [Dev Containers](https://code.visualstudio.com/docs/remote/containers). Puedes [instalar VSCode aquí](https://code.visualstudio.com/download). Existen 2 maneras de correr Dev Containers: GitHub Codespaces y localmente.

#### Desarrollo en GitHub Codespaces

Codespaces es un servicio de GitHub que permite correr VSCode en la nube.
Provee una cantidad limitada de horas de uso, que puede ser [expandida activando la cuenta Pro gratis a estudiantes](https://education.github.com/discount_requests/application).

- Instala la extensión de [GitHub Codespaces](https://marketplace.visualstudio.com/items?itemName=GitHub.codespaces).
- Crea o abre un Codespace desde el botón en la esquina superior derecha de este repositorio (o desde el menú de VSCode). Si no lo has creado, ingresa `open-source-uc/planner` como el repositorio a abrir.

Sigue en la sección [Desarrollo general](#desarrollo-general).

- Una vez terminado de desarrollar, [detén el Codespace](https://docs.github.com/es/codespaces/developing-in-codespaces/stopping-and-starting-a-codespace) para no consumir horas de uso. También puedes usar un [timeout para que se detenga automáticamente](https://docs.github.com/es/codespaces/customizing-your-codespace/setting-your-timeout-period-for-github-codespaces).

### Desarrollo local

- Instala [Docker](https://www.docker.com/). Asegurate que esté corriendo.
- Instala la extensión [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).
- Clona este repositorio y abre el proyecto en VSCode.
- Corre el comando `Dev Containers: Open Folder in Container` o has click en el popup que saldrá al abrir el proyecto.

Sigue en la sección [Desarrollo general](#desarrollo-general).

### Desarrollo general

- El Dev Container correrá automaticamente el setup necesario con `just init`. Espera que termine para continuar.
- Utiliza `Run and Debug` de VSCode con `Launch all 🚀` para correr todos los servicios al mismo tiempo. Espera que el backend (que puedes inspeccionar en `Python Debug Console`) termine de correr para continuar (cuando se muestre _"Aplication startup complete"_).

Una vez listo, podrás entrar a la app en [http://localhost:3000](http://localhost:3000) 🎉


Necesitaras un nombre de usuario para acceder a CAS. Puedes acceder con `testuser` o con otros usuarios definidos en `cas-mock-users.json`. 


Para realizar acciones sobre el repositorio (migraciones, generación de código, etc) puedes usar:
- el task runner de VSCode (<kbd>Ctrl/Cmd</kbd> + <kbd>Shift</kbd> + <kbd>P</kbd> -> _"Tasks: Run Task"_).
- `just` en la linea de comandos. Para ver comandos disponibles, corre `just` desde cualquier carpeta.

Es importante que cuando:
- Cambias la estructura de la API, corras la tarea _"Generate client"_ (también disponible en modo watch).
- Cambies el esquema de la base de datos, corras la tarea _"Create/apply migrations"_ para que los cambios se reflejen en la base de datos.

Para realizar contribuciones, revisa [contributing.md](contributing.md).

### Bug Reports & Feature Requests

> **Nota:** Este proyecto usa [Linear](https://linear.app/) para rastrear el progreso del proyecto. Por ahora, el Linear no es público, pero de todas formas se revisan los issues y features creados en GitHub.

La app aún está en una etapa muy temprana del desarrollo por lo que podrían haber cosas que no funcionan correctamente o difieren de la documentación, por lo que cualquier lector siéntase libre a colaborar :rocket:. Toda ayuda es bienvenida :)

## Mocks

El proyecto se integra con dos servicios externos: SIDING (para acceder a mallas y datos de estudiantes) y CAS (para el login UC). Ambos son configurables por medio de variables de entorno, y se proveen mocks para ambos servicios en caso de no tener credenciales para acceder a ellos.

- Para SIDING se provee un mock que se activa automáticamente en ausencia de credenciales. El mock es limitado, y solo permite probar algunas combinaciones de malla.
- Para CAS, se provee el servicio `cas-server-mock` que corre automáticamente junto a la app. Las cuentas de usuario disponibles son configurables en el archivo `cas-mock/data/cas-mock-users.json`.

## Staging y Producción

### Staging Server

El ambiente de staging está diseñado para testear las nuevas versiones del planner en un ambiente real antes de pasar a producción.

En primer lugar, es necesario generar manualmente los archivos `.env` y reemplazar los valores según corresponda para cada servicio utilizando los ejemplos ubicados en cada carpeta:
- _API_ → `backend/.env.staging`
- _servidor web_ → `frontend/.env.staging`
- _base de datos_ → `database/.env.staging`

Luego, para correr la aplicación utilizando un servidor mock de **CAS externo** se debe:
1. Definir las variables `CAS_SERVER_URL` y `CAS_LOGIN_REDIRECTION_URL` en `backend/.env` con la URL del servidor externo.
2. Levantar los contenedores con `docker compose up planner -d --build` desde la raíz del repositorio.

Alternativamente, para correr la aplicación utilizando un servidor mock de **CAS local**:
1. Dejar las variables `CAS_SERVER_URL` y `CAS_LOGIN_REDIRECTION_URL` en `backend/.env` con los valores predeterminados del archivo de ejemplo `.env.staging`.
2. Luego, es necesario generar el archivo `cas-mock-users.json` en `cas-mock/data` a partir del ejemplo `cas-mock-users.json.example`.
3. Levantar los contenedores con `docker compose up -d --build` desde la raíz del repositorio.

Finalmente, se puede detener la app con `docker compose down` desde la raíz del repositorio.

### Producción

El ambiente de producción es manejado por la universidad de forma interna, por lo que aquí se detallan las **instrucciones para desplegar el planner** de forma manual:
1. Se deben crear tres archivos `.env`, uno por cada servicio y dentro de su respectiva carpeta:
- `backend/.env` a partir del ejemplo `backend/.env.production` (_API_)
- `frontend/.env` a partir del ejemplo `frontend/.env.production` (_servidor web_).
- `database/.env` a partir del ejemplo `database/.env.production` (_base de datos_).
2. Reemplazar los valores de las variables de entorno según corresponda en todos los archivos `.env` creados. **IMPORTANTE:** no olvidar modificar la variable `JWT_SECRET` en `backend/.env` y otras variables que puedan contener secretos para evitar vulnerabilidades de seguridad.
- Para generar una clave `JWT_SECRET` segura y aleatoria se puede utilizar el comando `openssl rand -base64 32`.
3. Levantar los contenedores con `docker compose up planner -d --build` desde la raíz del repositorio. Requiere _Docker_ y _Docker Compose_ instalados en la máquina.
4. Revisar el estado de los contenedores con `docker ps` o `docker container ls`.
5. Finalmente, se puede detener la app con `docker compose down` desde la misma ubicación.

Nota: los comandos podrían variar ligeramente dependiendo del sistema operativo y versión de *Docker Compose*. En particular, podría ser necesario utilizar `docker-compose` en vez de `docker compose` y `sudo docker compose` en vez de `docker compose`.

---

Cabe mencionar que sería ideal a futuro implementar un **despliegue automático del planner** utilizando técnicas de *CI/CD*, pero de momento esta opción se pospone debido a las restricciones de seguridad y requerimientos de la universidad para hacer un despliegue interno.

## Equipo

- [@shantifabri](https://github.com/shantifabri) - Coordinación / Frontend
- [@Diegothx](https://github.com/Diegothx) - Frontend
- [@negamartin](https://github.com/negamartin) - Backend
- [@fagiannoni](https://github.com/fagiannoni) - Backend
- [@agucova](https://github.com/agucova) - Apoyo Backend/Frontend

## Licencia

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](./license.md)

<p align="right">(<a href="#readme-top">volver arriba</a>)</p>
