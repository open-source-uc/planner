
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

Un ramo puede tener equivalencias, que se deberian considerar como identicos al momento de validar requerimientos.

Segun https://registrosacademicos.uc.cl/wp-content/uploads/2022/07/Inscripcion-de-cursos-alumnos-201722-v2.pdf:

> Equivalencias: Permite conocer si la asignatura en cuestión tiene equivalencias, es decir, asignaturas con
> programas de estudio similares. Esto significa que el aprobar una de ellas, es equivalente a haber aprobado
> otra u otras.

Propiedades observadas del [catalogo UC](https://catalogo.uc.cl/):
- La relacion pareciera ser conmutativa, al menos en los 4000+ cursos dictados el 2022-2.
- La relacion no es transitiva. Eg: FIS1512 es equivalente a ICE1003, y ICE1003 es equivalente a FIS1513, pero FIS1512 no es equivalente a FIS1513.

No queda claro si es una relacion de equivalencia.

## Ramos especiales

Hay ramos con Aprob. Especial, que requieren autorización de la DIPRE para tomar.
(Posiblemente esto corresponde al campo `is_special`?)

## Estados de un ramo

Estados de un curso:

A: aprobado
R: reprobado?
C: ramo convalidado de otra universidad, pero sin nota
I: ramo incompleto, aun no puede ser calificado (ie. ramo anual)
P: ramo pendiente, esta temporalmente no-aprobado hasta que se pruebe lo contrario
    Notar que segun [https://registrosacademicos.uc.cl/informacion-para-estudiantes/inscripcion-y-retiro-de-cursos/preguntas-frecuentes/]
    si se considera como aprobado para efectos de requisitos.
D?: algunos labs pueden tener nota D (distinguido = nota 7.0) no se si esto es un estado o una nota

Fuente: https://registrosacademicos.uc.cl/informacion-para-estudiantes/inscripcion-y-retiro-de-cursos/evaluacion-y-calificacion-de-un-curso/