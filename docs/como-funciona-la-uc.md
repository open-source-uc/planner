
# Conocimiento acumulado sobre como funcionan los ramos y las mallas

Anotar la informacion que aprendemos sobre como funcionan los ramos en la UC
en este documento.

## Diferencia entre Banner y Seguimiento Curricular

Hay dos sistemas de reglas completamente independientes que un alumno tiene que
cumplir al tomar ramos en la UC:

- Banner: Al tomar ramos, el sistema Banner le puede impedir fisicamente tomar
    un ramo si no cumple los requisitos o restricciones.
    Banner es un sistema closed-source desarrollado por la
    empresa estadounidense Ellucian.
    La UC compra este servicio.
    Por ende, no tenemos un contacto a quien preguntar sobre el funcionamiento
    preciso de Banner.
- Seguimiento Curricular: Al terminar la carrera, funcionarios de la UC juzgan
    si el alumno cumple los requisitos para licenciarse o titularse.
    Este es un proceso complejo, pero gran parte del proceso es mirar la app
    de Seguimiento Curricular en SIDING, que valida que los ramos tomados se
    ajusten a la malla de ingenieria, con el major, minor y titulo elegido por
    el alumno.

En Planner, ambos sets de reglas se validan independientemente, bajo
`plan.validation.courses` y `plan.validation.curriculum`, respectivamente.

## Requisitos y restricciones

Un ramo puede tener requisitos y/o restricciones.
En caso de haber ambos, se conectan por un conector lógico `y` o `o`.

Los requisitos son una expresion logica, un arbol donde los operadores son `y` o
`o`, y las hojas del arbol son siglas de ramos que se han de haber tomado antes
de tomar el ramo en consideracion.
Estas hojas del arbol pueden estar opcionalmente marcadas como correquisitos
(marcados con el sufijo `(c)`), lo que permite que el ramo se tome el mismo semestre
que el ramo en consideracion y aun asi contar como cumplido.
En caso contrario, el semestre del requisito ha de ser estrictamente menor al
semestre del ramo en consideracion.

Las restricciones son un poco más complejas, tienen la misma estructura de árbol
logico que los requisitos, pero las hojas del árbol no son ramos, son igualdades
y desigualdades de la forma `A = B`, `A >= B` o `A <> B`.

Hay 5 posibles lados izquierdos para estas (des)igualdades, cada uno con sus lados derechos asociados:

- `Nivel`: El lado derecho puede tomar 4 posibilidades.
    - `Pregrado`
    - `Magister`
    - `Doctorado`
    - `Postitulo`

    Se usa el operador `=`, pero parece que semanticamente debiera ser `>=` (TODO: confirmar esto).
    Eso si, existe exactamente 1 ramo en todo el catalogo que no usa `=`, y usa `<>`, que es
    `PSI4050`.
- `Escuela`: La facultad. Se usa el operador `=` y `<>`.
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
- `Creditos`: Cantidad total de creditos aprobados. Se usa `>=` con un valor
    numerico.
    Banner no sabe sobre la malla que toma un alumno.
    Por ende, para esta restriccion cuentan todos los ramos que ha tomado un
    alumno, incluyendo los ramos duplicados (TODO: Confirmar esto).

## Equivalencias

Catalogo UC, que refleja la informacion de Banner, define equivalencias.
Ademas, el servicio de SIDING define igualmente equivalencias que son utilizadas
por seguimiento curricular.

### Equivalencias UC

Un ramo puede tener equivalencias UC, que se deberian considerar como identicos al momento de validar requerimientos.

Segun https://registrosacademicos.uc.cl/wp-content/uploads/2022/07/Inscripcion-de-cursos-alumnos-201722-v2.pdf:

> Equivalencias: Permite conocer si la asignatura en cuestión tiene equivalencias,
> es decir, asignaturas con programas de estudio similares. Esto significa que el
> aprobar una de ellas, es equivalente a haber aprobado otra u otras.

Propiedades observadas del [catalogo UC](https://catalogo.uc.cl/):
- La relacion pareciera ser conmutativa, al menos en los 4000+ cursos dictados el 2022-2.
    **Pero no en los cursos obsoletos!**: La sigla ING1001 (practica I) es
    equivalente con IPP1000 (practica 1 obsoleta), pero IPP1000 no es equivalente con
    ING1001.
    Por evidencia empirica, tomar ING1001 hace que IPP1000 cuente como aprobado
    para efectos de requisitos.
    Por ende, hay dos escenarios posibles:
    1. Solo sirven las equivalencias "inversas".
    2. Sirven las equivalencias "directas" y las equivalencias "inversas".
    De todas formas, no hay ningun requisito que se cumpla bajo el escenario
    *2* pero no bajo el escenario *1*, por lo que en la practica no importa
    cual implementemos.
- La relacion no es transitiva. Eg: FIS1512 es equivalente a ICE1003, y ICE1003 es
    equivalente a FIS1513, pero FIS1512 no es equivalente a FIS1513.
    Es posible que Banner automaticamente "propague" las equivalencias
    transitivas.
    TODO: Hacer una prueba experimental.

### Equivalencias SIDING

Las equivalencias SIDING afectan la manera en que Seguimiento Curricular calcula
si una malla es satisfecha o no.
En particular, SIDING deduplica los ramos segun las equivalencias.

## Mallas y Seguimiento Curricular

En la teoria, para determinar si un alumno cumple con los requisitos para
licenciarse o titularse, existe un set de documentos `.pdf` llamados "Plan
de Estudios", que son la fuente autoritativa sobre el tema.
Estos documentos estan disponibles en SIDING bajo
`Pregrado > Ciclo 1 > Planes de Estudios`.
Incluso, si la UC se niega a entregar el titulo a un alumno, pero este considera
que el Plan de Estudios indica que debiera poder titularse, puede reclamar casi
como si fuera un juicio. (Fuente: reunion con el equipo de desarrollo de SIDING)

En la practica, para determinar si un alumno se puede titular un funcionario
ingresa a la app de Seguimiento Curricular y comprueba visualmente que cumpla
con todos los requisitos.
Esto es, literalmente ver que todas las cajas esten en verde.

Seguimiento Curricular es un espagueti que toma los cursos que ha aprobado un
alumno y produce un documento `.html` con colores, hecho para facilitarle la vida
a los funcionarios UC.
En nuestro caso, consideramos Seguimiento Curricular como la Fuente de la Verdad,
y el Planner debiera alinearse a su juicio.
Dado que no hay una especificacion formal para Seguimiento Curricular (aparte del
documento de Plan de Estudio, que como cualquier documento legal es bastante
ambiguo), y ademas Seguimiento Curricular no ofrece una API, nos vemos forzados a
reimplementarlo "lo mejor que podamos".

Como dato, el nucleo de desarrollo SIDING planea reimplementar Seguimiento Curricular
de manera que el output sea mas computer-friendly, y exponer una API.
Lamentablemente, esto estaria listo a lo mas temprano el 2024, por lo que no podemos
aprovecharlo.

## Algoritmo utilizado por Seguimiento Curricular

Para determinar que bloques de la malla estan satisfechos por la carga academica
de un alumno, Seguimiento Curricular sigue el siguiente pseudocodigo:

```
# Los bloques de `malla` estan ordenados segun el orden en que aparecen en el
# documento de Plan de Estudio.

# `cursos_aprobados` esta ordenado por semestre, con los empates desambiguados
# por sigla alfabeticamente.
# Ademas, los cursos estan deduplicados segun las equivalencias SIDING.
# Los ramos de seleccion deportiva son una excepcion, se permiten hasta 2
# instancias.
# TODO: Averiguar exactamente como funciona esta deduplicacion

for bloque in malla:
    for curso in cursos_aprobados:
        if bloque.es_satisfecho_por(curso):
            bloque.satisfacer()
            cursos_aprobados.delete(curso)
```

Ademas, los bloques de exploratorio, biologico, y optativo de fundamentos de
ingenieria se pueden asignar manualmente a cursos particulares, para aliviar casos
borde en que esta asignacion falla.

## La importancia del nombre de un ramo

Algunos tipos de ramos reciben trato especial.
Por ejemplo, el algoritmo de deduplicacion de SIDING trata los ramos de seleccion
deportiva de SIDING especialmente.
Para identificar que ramos particularmente son selecciones deportivas, se utiliza
una heuristica: el nombre del ramo.

De manera parecida, los cursos IPre cuentan como optativo de ingenieria, y estos
se identifican con el nombre "Investigacion o Proyecto".

## Ramos especiales

Hay ramos con Aprob. Especial, que requieren autorización de la DIPRE para tomar.
(Posiblemente esto corresponde al campo `is_special`?)

## Estados de un ramo

Estados de un curso:

**A**: Aprobado.

**R**: Reprobado?

**C**: Ramo convalidado de otra universidad, pero sin nota.

**I**: Ramo incompleto, aun no puede ser calificado. (ie. ramo anual)

**P**: Ramo pendiente, esta temporalmente no-aprobado hasta que se pruebe lo contrario.
    Notar que segun
    [https://registrosacademicos.uc.cl/informacion-para-estudiantes/inscripcion-y-retiro-de-cursos/preguntas-frecuentes/]
    si se considera como aprobado para efectos de requisitos.

**D**?: Algunos labs pueden tener nota D. (distinguido = nota 7.0)
    Anecdotico: Conozco a alguien que tiene nota D en intro a la progra, tras
    convalidarla por examen de conocimientos relevantes.
    Sin embargo, conozco a otras personas que tambien la convalidaron, pero tienen
    nota numerica normal.

Pareciera que mas que estados, son notas que puede tener un ramo, tomando el lugar
que normalmente usaria una nota numerica del 1 al 7.

Fuente: https://registrosacademicos.uc.cl/informacion-para-estudiantes/inscripcion-y-retiro-de-cursos/evaluacion-y-calificacion-de-un-curso/
