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
  <a href="#staging-server-y-producción">Staging Server y Producción</a> •
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
- Para CAS, se provee el servicio `cas-server-mock` que corre automáticamente junto a la app. Las cuentas de usuario disponibles son configurables en el archivo `backend/mock-data/cas-mock-users.json`.

## Staging Server y Producción

Esta sección aún está en ideación y desarrollo.

### Staging Server

El ambiente de staging está diseñado para testear las nuevas versiones en un ambiente real antes de pasar a producción.



Levantar los servicios en diferentes contenedores utilizando:

> docker compose -f docker-compose.yml -f docker-compose.stag.yml up -d --force-recreate --build

Detener los contenedores con el siguiente comando:

> docker compose -f docker-compose.yml -f docker-compose.stag.yml down

### Producción

El ambiente de producción lo maneja la universidad de forma interna, pero aquí se intentan detallar los pasos para poder replicar el funcionamiento.

1. Se debe crear un archivo `.env` en la carpeta `backend`. Si es que no existe tal archivo, entonces se utilizará de forma predeterminada el archivo de ejemplo `backend/.env.staging.example`.
2. Modificar otras variables de entorno directamente en el archivo `docker-compose.prod.yml` (e.g. credenciales de la base de datos y URL del planner).
- POR DISCUTIR: ¿hacer que todas las variables se puedan configurar a través de un `.env` en vez de cambiarlas directamente en el `docker-compose.prod.yml`?
3. Levantar toda la aplicación utilizando el siguiente comando (requiere _Docker_ y _Docker Compose_ instalados en la máquina):

> docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --force-recreate --build

4. Detener los contenedores con el siguiente comando:

> docker compose -f docker-compose.yml -f docker-compose.prod.yml down

## Equipo

- [@shantifabri](https://github.com/shantifabri) - Coordinación / Frontend
- [@Diegothx](https://github.com/Diegothx) - Frontend
- [@negamartin](https://github.com/negamartin) - Backend
- [@fagiannoni](https://github.com/fagiannoni) - Backend
- [@agucova](https://github.com/agucova) - Apoyo Backend/Frontend

## Licencia

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](./license.md)

<p align="right">(<a href="#readme-top">volver arriba</a>)</p>
