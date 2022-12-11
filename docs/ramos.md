
# Conocimiento acumulado sobre como funcionan los ramos y las mallas

Anotar datos útiles sobre como funcionan acá.

## Requisitos y restricciones

Un ramo puede tener requisitos y/o restricciones. En caso de haber ambos, se conectan por un conector lógico `y` o `o`.

Los requisitos son simplemente ramos que se han de tomar antes de tomar el ramo.
Los correquisitos se pueden tomar el mismo semestre.

Las restricciones son un poco más complejas, tienen la misma estructura de árbol que los requisitos,
pero las hojas del árbol no son ramos, son igualdades y desigualdades de la forma `A <=> B`, con `<=>`
un operador de comparación que puede ser `=`, `>=` o `<>` (operador de desigualdad). La fuente actual
de datos (el scraper de buscacursos) no soporta el operador `<>`. Se ha de incluir cuando tengamos una
fuente más oficial.

Hay 5 posibles lados izquierdos para estas (des)igualdades, cada uno con sus lados derechos asociados:

- `Nivel`: El lado derecho puede tomar 4 posibilidades. Se usa el operador `=`, pero semanticamente debiera ser `>=`.
    - `Pregrado`
    - `Magister`
    - `Doctorado`
    - `Postitulo`
- `Escuela`: La facultad. Se usa el operador `=` (y podria usarse `<>` en un futuro, aunque ahora no se usa)
    - `Matemáticas`
    - `College`
    - `Ingenieria`
    - `Arte`
    ...
- `Programa`: Parecieran ser programas estilo magister/doctorado. Se usa `=` y `<>`.
    - `Mag Tecnol De Inform`
    - `Medicina`
    - `Doct Educacion`
- `Carrera`: Autoexplicativo. Se usa `=` y `<>`.
    - `Medicina`
    - `Comunicaciones`
    - `Ingenieria`
- `Creditos`: Cantidad total de creditos aprobados. Se usa `>=` con un valor numerico.

## Equivalencias

Un ramo puede tener equivalencias. TODO: Investigar
