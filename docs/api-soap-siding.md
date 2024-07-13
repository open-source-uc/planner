
# Detalles importantes sobre la API SOAP de Siding

## Overview

La API de Siding es un webservice SOAP.
Esto significa que la interfaz es definida por un archivo `.wsdl`.
El URL de este archivo se entrega a Planner a través de variables de entorno en producción, y los desarrolladores con acceso al webservice pueden ingresarlo también en el ambiente de desarrollo.

## Observaciones de la API

- Cuando el webservice entrega una lista vacía, muchas veces entrega un valor nulo en lugar de la lista vacía.
- Los planes de estudio están bastante incompletos, hay muchas reglas no representables en el formato utilizado.

Estas observaciones posiblemente están desactualizadas:

- El endpoint `getConcentracionCursos` lanza un XML invalido para combinaciones invalidas de major-minor-titulo (pero arroja status 200 OK). Tambien lo lanza para algunas combinaciones validas (eg. `C2020-M073-N206-40006`).
- Faltan muchos datos.
    Casi todas las combinaciones excepto algunas como `C2020-M170-N776-40082` entregan una lista vacia en `getMallaSugerida`.
- Hay majors sin minors asociados, como `M186 - Major en Ingenieria Civil - Track en Diseno y Construccion de Obras`.
    Esto es correcto segun nuestra reunion con Daniela: algunos majors ya tienen los minors "incluidos".
