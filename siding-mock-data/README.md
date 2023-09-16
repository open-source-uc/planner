# Mock de SIDING

El Planner se comunica con una API web de SIDING a la que coloquialmente nos referimos como "el webservice".
De aca puede extraer informacion como la carga academica de los alumnos, las mallas sugeridas para distintos
planes, el listado de majors/minors/titulos, e incluso los cursos disponibles.

De la informacion que expone, actualmente (2023-09-16) el Planner solo se conecta con SIDING regularmente
para obtener la informacion de carga academica de los alumnos.
El listado de programas y las mallas sugeridas se empaquetan junto al Planner, y el listado de cursos se
obtiene scrapeando catalogo UC y buscacursos en lugar de consultar con SIDING.

La razon por la que las mallas sugeridas se empaquetan con Planner, es porque los planes de estudio no estan
bien definidos en ningun lugar, y por ende las mallas que entrega SIDING no son exactamente completas.
Por ende, Planner tiene que "cocinar" las mallas a partir de informacion de distintas fuentes, en particular
desde la informacion que entrega SIDING, la informacion scrapeada desde los PDFs de los planes de estudio y
reglas adicionales hardcodeadas a mano.

Como el proceso de mezclar esta informacion de distintas fuentes es complejo y fragil, nos gustaria que
no dependiera de datos que pueden cambiar en cualquier momento, como por ejemplo los datos que entrega el
webservice en vivo.
Para evitar esto, se "congelan" los datos que entrega el webservice en un momento particular de tiempo, y
luego el planner funciona con estos datos descargados.
El contra de esto es que si SIDING actualiza las mallas Planner requiere de intervencion manual para
actualizarse. Esto no es tan grave ya que debiera ser solo correr un script y pushear (siempre que no se
rompa nada con los datos nuevos).
El pro de esto es que Planner no se puede romper con cambios al webservice de SIDING. Esto ya ha ocurrido
antes, y por ende es importante que Planner sea resiliente a estos cambios.

Los datos se encuentran empaquetados en la forma de un "mock".
El mock es como un diccionario: almacena respuestas del webservice a distintas consultas.
Luego, cuando el Planner hace un request a SIDING, automaticamente se hace una consulta en este diccionario.
Si ya hay una respuesta almacenada, entonces se responde la consulta localmente sin nunca tocar el
webservice.

## Formato de los datos

El mock se construye a partir de varios sub-mocks.
La razon para hacer esto es que parte del mock se ingresa a mano (por ejemplo los usuarios de prueba), y
otra parte del mock se genera automaticamente (por ejemplo la informacion congelada sobre las mallas).

El archivo `index.json` contiene una lista ordenada de los nombres de los archivos que componen el mock.
El mock final se construye juntando todos los mocks listados en `index.json`.
Si dos mocks especifican respuestas distintas para la misma consulta, el mock que se liste más tarde
sobreescribe el mock que se liste primero.

En particular, el estado actual de `index.json` es:
- `mallas.json`: Este archivo contiene las mallas tal cual las entrega SIDING.
    Se genera automaticamente.
    Cuando SIDING actualiza las mallas hay que regenerar este archivo.
- `listado-con-versiones.json`: El webservice esta actualmente roto y no entrega las versiones de
    curriculum asociadas a cada major/minor/titulo.
    Por suerte en algun momento descargué el listado, y esta es una version congelada que si tiene
    las versiones de curriculum.
    Sobreescribe el listado de major/minor/titulo en `mallas.json`.
- `test-data.json`: Contiene los usuarios de prueba, utiles para probar el planner en local.

## Actualizar los datos desde SIDING

El archivo `/siding-mock-data/mallas.json` contiene las mallas tal cual como las entrega SIDING.
Para actualizarlas (por ejemplo, cuando SIDING hace una actualizacion en las mallas), se puede hacer
automaticamente con el _script_ en `/backend/scripts/download_mallas.py`.
Es necesario tener configuradas las claves de acceso al webservice en `/backend/.env`.
