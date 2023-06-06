<h1 align="center">
  <br>
  <a href=# name="readme-top">Proyecto Planner</a>
</h1>

<p align="center">
     <!-- Badges Here -->
</p>

<p align="center">
  <a href="#Descripción">Descripción</a> •
  <a href="#Uso">Uso</a> •
  <a href="#Contribuir">Contribuir</a> •
  <a href="#Equipo">Equipo</a> •
  <a href="#Licencia">Licencia</a>
</p>

<h4 align="center">
  <a href=# name="readme-top"><img src="./docs/img/demo_gif.gif" width="700px" alt="banner"></a>
</Es>

---

## Descripción

Este es el hogar para el desarrollo del nuevo Planner de Ingeniería UC, hecho por estudiantes para estudiantes.

Tras varios años en ideación, este proyecto se lanzó como [una propuesta conjunta](https://drive.google.com/file/d/1IxAJ8cCzDkayPwnju5kgc2oKc7g9fvwf/view) entre la Consejería Académica de Ingeniería y Open Source UC, con el propósito de reemplazar el [actual planner de Ingeniería](https://planner.ing.puc.cl/). La propuesta, tras ser aprobada por la Escuela de Ingeniería, dió comienzo al proyecto en modalidad de marcha blanca. A principios del 2023, y con un MVP listo, la Dirección de Pregrado oficialmente aprobó la continuación del desarrollo del proyecto.

## Instalación y desarrollo

La forma óptima de correr el proyecto, sin tener que instalar todas las dependencias, es utilizar el [developement container](https://containers.dev/) para VSCode. El contenedor viene completamente configurado y listo para correr el proyecto.

### Pasos sugeridos

1. Instala [Visual Studio Code](https://code.visualstudio.com/) y [Docker](https://www.docker.com/). En VSCode, instala la extensión [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).
   - También puedes abrir este repositorio con [GitHub Codespaces](https://github.com/features/codespaces). Esto no requiere configuración.
2. Al abrir el proyecto en VSCode, la extensión Dev Containers debería aparecer un _pop up_ con la opción de "Reabrir en contenedor".
3. Espera a que se corra la tarea de inicio `just init`. Esto instala las depedencias y crea archivos como `.env` y `cas-mock-users.json`, que son necesarios para correr el proyecto.
   - El proyecto se integra con dos servicios externos: SIDING (para acceder a mallas y datos de estudiantes) y CAS (para el login UC). Ambos son configurables por medio de variables de entorno.
   - Se proveen mocks para ambos servicios en caso de no tener credenciales para acceder a ellos.
   - Para SIDING se provee un mock que se activa automáticamente en ausencia de credenciales. El mock es limitado, y solo permite probar algunas combinaciones de malla.
   - Para CAS, se provee el servicio `cas-server-mock` que corre automáticamente junto a la app. Las cuentas de usuario disponibles son configurables en el archivo `data/cas-mock-users.json`.
4. En la sección "Run and Debug" de VSCode aparecerán acciones para correr cada servicio de la app por separado, o todos al mismo tiempo (`Launch all 🚀`).
   - Adicional a esto, se proveen tareas para distintas acciones de utilidad, como resetear   migrar la base de datos, generar el cliente de la API, abrir [Prisma Studio](https://www.prisma.io/studio), etc. 
   - Puedes ver las tareas disponibles con el comando `"Tasks: Run Task"` (Ctrl/Cmd + Shift + P).
   - También se dispone de un [task runner](https://github.com/casey/just) en la linea de comandos. Para ver comandos disponibles, corre `just` desde cualquier carpeta.

Una vez abierto, todos los cambios en el código debiesen reflejarse automáticamente en tu navegador, sin necesidad de recargar la página.

Hay dos excepciones a esto: cambios en la estructura de la API y cambios en el esquema de la base de datos. En el primer caso, debes correr la tarea "Generate client" (también disponible en modo watch). En el segundo caso, debes correr la tarea "Create/apply migrations" para que los cambios se reflejen en la base de datos.

<p align="right">(<a href="#readme-top">volver arriba</a>)</p>

## Contribuir

### Workflow

> El workflow es PR a development -> Revisar preview y checks -> Asignar reviewers -> Aprobación -> Merge a development

La información detallada sobre cómo contribuir se puede encontrar en [contributing.md](contributing.md).

### Bug Reports & Feature Requests

> **Nota:** Este proyecto usa [Linear](https://linear.app/) para rastrear el progreso del proyecto. Por ahora, el Linear no es público, pero de todas formas se revisan los issues y features creados en GitHub.

La app aún está en una etapa muy temprana del desarrollo por lo que podrían haber cosas que no funcionan correctamente o difieren de la documentación, por lo que cualquier lector siéntase libre a colaborar :rocket:. Toda ayuda es bienvenida :)

## Equipo

- [@shantifabri](https://github.com/shantifabri) - Coordinación / Frontend
- [@Diegothx](https://github.com/Diegothx) - Frontend
- [@negamartin](https://github.com/negamartin) - Backend
- [@fagiannoni](https://github.com/fagiannoni) - Backend
- [@agucova](https://github.com/agucova) - Apoyo Backend/Frontend

## Licencia

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](./license.md)

<p align="right">(<a href="#readme-top">volver arriba</a>)</p>
