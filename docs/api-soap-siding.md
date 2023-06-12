
# Detalles importantes sobre la API SOAP de Siding

## Overview

La API de Siding es un webservice SOAP.
En primer lugar, esto significa que la interfaz esta definida en buena parte por un archivo `.wsdl`,
actualmente disponible en https://intrawww.ing.puc.cl/siding/ws/ServiciosPlanner_test1.wsdl.

Tomar en cuenta que el `_test1` probablemente significa que el URL cambiara en algun momento.

Para hacer que el servicio sea robusto, descargue un snapshot de este archivo y esta embeddeado en
el planner mismo.
En un futuro, seria bueno comparar la copia hardcodeada con la copia remota, para detectar cambios en
la API remota.

## Correcciones al spec `.wsdl`

El archivo `.wsdl` tal como es proveido no funciona con otro cliente que no sea `SoapClient` de PHP.

Actualmente, solo hay 1 problema, que en teoria esta en proceso de ser arreglado:

- El atributo `location` del servicio esta mal definido, le falta un `/`:

Original:

```xml
<soap:address location="https://intrawww.ing.puc.cl/siding/ws/ServiciosPlanner_test1" />
```

Arreglado:

```xml
<soap:address location="https://intrawww.ing.puc.cl/siding/ws/ServiciosPlanner_test1/" />
```

## Observaciones de la API

- El endpoint `getConcentracionCursos` lanza un XML invalido para combinaciones invalidas de major-minor-titulo (pero arroja status 200 OK). Tambien lo lanza para algunas combinaciones validas (eg. `C2020-M073-N206-40006`).
- Faltan muchos datos.
    Casi todas las combinaciones excepto algunas como `C2020-M170-N776-40082` entregan una lista vacia en `getMallaSugerida`.
- Hay majors sin minors asociados, como `M186 - Major en Ingenieria Civil - Track en Diseno y Construccion de Obras`.
    Esto es correcto segun nuestra reunion con Daniela: algunos majors ya tienen los minors "incluidos".
