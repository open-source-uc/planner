"""
En este archivo se concentran las transformaciones sobre las mallas que debemos hacer,
pero que no estan especificadas por SIDING de forma computer-readable, y por ende
tenemos que implementar en Python.

Como este codigo es especifico a SIDING y probablemente tenga que ser tocado por otra
gente en un futuro, los comentarios estan en español al contrario del resto del codigo.

Cuando aparezca una nueva version del curriculum con reglas especificas, este codigo es
el que habra que tocar.
"""


from unidecode import unidecode

from app.plan.course import EquivalenceId, pseudocourse_with_credits
from app.plan.courseinfo import CourseDetails, CourseInfo, EquivDetails, add_equivalence
from app.plan.validation.curriculum.tree import (
    SUPERBLOCK_PREFIX,
    Block,
    Combination,
    Curriculum,
    CurriculumSpec,
    FillerCourse,
    Leaf,
    Multiplicity,
)


def _set_block_layer(block: Block, layer: str):
    if isinstance(block, Leaf):
        block.layer = layer
    else:
        for subblock in block.children:
            _set_block_layer(subblock, layer)


def _ceil_div(a: int, b: int) -> int:
    """
    Compute `ceil(a / b)` without floating point errors.
    """
    return -(a // -b)


def _skip_extras(curriculum: Curriculum):
    # Saltarse los ramos de 0 creditos del bloque de "Requisitos adicionales para
    # obtener el grado de Licenciado...", excepto por la Practica I
    # Razones:
    # - Hay un ramo que se llama "Aprendizaje Universitario" que no sale en Seguimiento
    #   Curricular, y ni idea que es
    # - El test de ingles tiene requisitos incumplibles de forma normal, por lo que el
    #   recomendador no logra colocarlo
    # - Es buena idea mantener la practica si, porque hay algunos ramos que tienen la
    #   practica de requisito.
    #   Tambien, la practica puede contar como optativo de fundamentos. Para que la
    #   practica no se pinte de Plan Comun, hay que dirigirla a otro bloque.
    # Esto significa que los cursos no tendran un bloque para el que contar y no se
    # generaran automaticamente. Sin embargo, si un estudiante los tiene entre sus
    # cursos tomados los cursos no se eliminan.

    for superblock in curriculum.root.children:
        if not isinstance(superblock, Combination):
            continue
        if not all(block.cap == 1 for block in superblock.children):
            continue
        superblock.children = [
            b
            for b in superblock.children
            if "Practica" in b.debug_name or "Práctica" in b.debug_name
        ]


# Tabla que mapea la primera palabra del nombre textual de un bloque academico a un
# nombre mas machine-readable
C2020_SUPERBLOCK_TABLE = {
    "ciencias": "PlanComun",
    "base": "PlanComun",
    "formacion": "FormacionGeneral",
    "major": "Major",
    "minor": "Minor",
    "ingeniero": "Titulo",
}
C2022_SUPERBLOCK_TABLE = {
    "matematicas": "PlanComun",
    "fundamentos": "PlanComun",
    "formacion": "FormacionGeneral",
    "major": "Major",
    "minor": "Minor",
    "ingeniero": "Titulo",
}


def _identify_superblocks(spec: CurriculumSpec, curriculum: Curriculum):
    # Cambia los codigos de los bloques academicos a nombres "machine readable".
    # Por ejemplo, cambia "Ingeniero Civil en Computación" a 'title'
    for superblock in curriculum.root.children:
        if not superblock.block_code.startswith(SUPERBLOCK_PREFIX):
            continue
        # Heuristica: tomar la primera palabra, normalizarla (quitarle los tildes y todo
        # a minúscula) y buscar en una tabla hardcodeada.
        id_words = (
            unidecode(superblock.block_code[len(SUPERBLOCK_PREFIX) :]).lower().split()
        )
        if len(id_words) < 1:
            continue
        match spec.cyear.raw:
            case "C2020":
                superblock_table = C2020_SUPERBLOCK_TABLE
            case "C2022":
                superblock_table = C2022_SUPERBLOCK_TABLE
        superblock_id = superblock_table.get(id_words[0], "")
        superblock.block_code = f"{SUPERBLOCK_PREFIX}{superblock_id}"


# Identifica a los bloques de OFG.
C2020_OFG_BLOCK_CODE = "courses:!L1"
# Los cursos de optativo en ciencias.
C2020_OFG_SCIENCE_OPTS = {
    "BIO014",
    "EYP2355",
    "ELM2431",
    "EYP290I",
    "FIZ0314",
    "FIS1542",
    "FIZ0311",
    "FIZ0222",
    "FIZ0223",
    "FIZ0313",
    "FIZ1428",
    "MAT2205",
    "MAT255I",
    "MLM2221",
    "MLM2301",
    "MAT2305",
    "MLM2401",
    "MLM2411",
    "MLM251I",
    "MAT251I",
    "MLM2541",
    "MLM260I",
    "MAT2605",
    "QIM121",
    "QIM122",
    "QIM124",
    "QIM109A",
    "QIM130",
    "QIM200",
    "QUN1003",
    "MAT2565",
    "FIZ0315",
    "FIZ0312",
    "MAT380I",
    "FIS0104",
    "MAT270I",
    "QIM202",
    "FIZ0614",
    "FIZ2110",
}


def _merge_ofgs(curriculum: Curriculum):
    # Junta los bloques de OFG de 10 creditos en un bloque grande de OFG
    # El codigo de lista para los OFG es `!L1`
    for superblock in curriculum.root.children:
        if not isinstance(superblock, Combination):
            continue
        # Junta todos los bloques que son OFG en una lista
        l1_blocks: list[Leaf] = [
            block
            for block in superblock.children
            if isinstance(block, Leaf) and block.block_code == C2020_OFG_BLOCK_CODE
        ]
        if len(l1_blocks) > 0:
            # Elimina todos los bloques que son OFG de `superblock.children`
            superblock.children = [
                block
                for block in superblock.children
                if block.block_code != C2020_OFG_BLOCK_CODE
            ]
            # Juntar todos los bloques OFG en un bloque y agregarlo de vuelta
            total_cap = sum(block.cap for block in l1_blocks)
            superblock.children.append(
                Leaf(
                    debug_name=l1_blocks[0].debug_name,
                    block_code=C2020_OFG_BLOCK_CODE,
                    name=l1_blocks[0].name,
                    cap=total_cap,
                    codes=l1_blocks[0].codes,
                ),
            )


def _allow_selection_duplication(courseinfo: CourseInfo, curriculum: Curriculum):
    # Los ramos de seleccion deportiva pueden contar hasta 2 veces (la misma sigla!)
    # Los ramos de seleccion deportiva se definen segun SIDING como los ramos DPT que
    # comienzan con "Seleccion"
    for superblock in curriculum.root.children:
        if not isinstance(superblock, Combination):
            continue
        for block in superblock.children:
            if isinstance(block, Leaf) and block.block_code == C2020_OFG_BLOCK_CODE:
                for code in block.codes:
                    if not code.startswith("DPT"):
                        continue
                    info = courseinfo.try_course(code)
                    if info is None:
                        continue
                    if info.name.startswith("Seleccion ") or info.name.startswith(
                        "Selección ",
                    ):
                        # Permitir que cuenten por el doble de creditos de lo normal
                        curriculum.multiplicity[code] = Multiplicity(
                            group=[code],
                            credits=2 * info.credits,
                        )
                # Only do it once
                return


def _ofg_check_limited(info: CourseDetails):
    if info.credits != 5:
        return False
    return info.code.startswith(("DPT", "RII", "CAR")) or info.code in (
        "MEB158",
        "MEB166",
        "MEB174",
    )


def _ofg_is_limited(courseinfo: CourseInfo, code: str):
    info = courseinfo.try_course(code)
    if info is None:
        return True
    if info.code in C2020_OFG_SCIENCE_OPTS:
        return False
    return _ofg_check_limited(info)


def _ofg_is_unlimited(courseinfo: CourseInfo, code: str):
    info = courseinfo.try_course(code)
    if info is None:
        return True
    if info.code in C2020_OFG_SCIENCE_OPTS:
        return False
    return not _ofg_check_limited(info)


def _ofg_is_science(courseinfo: CourseInfo, code: str):
    info = courseinfo.try_course(code)
    if info is None:
        return True
    return info.code in C2020_OFG_SCIENCE_OPTS


def _limit_ofg10(courseinfo: CourseInfo, curriculum: Curriculum):
    # https://intrawww.ing.puc.cl/siding/dirdes/web_docencia/pre_grado/formacion_gral/alumno_2020/index.phtml
    # En el bloque de OFG hay algunos cursos de 5 creditos que en conjunto pueden
    # contribuir a lo mas 10 creditos:
    # - DPT (deportivos)
    # - RII (inglés)
    # - CAR (CARA)
    # - OFG plan antiguo (MEB158, MEB166 y MEB174)

    # Ademas, agrega hasta 10 creditos de optativo en ciencias.
    #
    # Se pueden tomar hasta 10 creditos de optativo de ciencias, que es una
    # lista separada que al parecer solo esta disponible en forma textual.
    # Los ramos de esta lista no son parte de la lista `!L1` que brinda
    # SIDING, y tampoco sabemos si esta disponible en otra lista.
    # La lista L3 se ve prometedora, incluso incluye un curso "ING0001
    # Optativo En Ciencias" generico, pero no es exactamente igual al listado
    # textual en SIDING.
    #
    # Referencias:
    # "Además, es válido para avance curricular de OFG máximo 1 curso
    # optativo en ciencias (10 cr.) de una lista de cursos Optativos de
    # Ciencia, o su equivalente, definida por el Comité Curricular de la
    # Escuela de Ingeniería."
    # https://intrawww.ing.puc.cl/siding/dirdes/web_docencia/pre_grado/optativos/op_ciencias/alumno_2020/index.phtml
    # https://intrawww.ing.puc.cl/siding/dirdes/web_docencia/pre_grado/formacion_gral/alumno_2020/index.phtml

    for superblock in curriculum.root.children:
        if not isinstance(superblock, Combination):
            continue
        for block_i, block in enumerate(superblock.children):
            if isinstance(block, Leaf) and block.block_code == C2020_OFG_BLOCK_CODE:
                # Segregar los cursos de 5 creditos que cumplan los requisitos
                limited: set[str] = set()
                unlimited: set[str] = set()
                science: set[str] = set()
                for code in block.codes:
                    if _ofg_is_limited(courseinfo, code):
                        limited.add(code)
                    if _ofg_is_unlimited(courseinfo, code):
                        unlimited.add(code)
                    if _ofg_is_science(courseinfo, code):
                        science.add(code)
                # Separar el bloque en 3
                limited_block = Leaf(
                    debug_name=f"{block.debug_name} (máx. 10 creds. DPT y otros)",
                    block_code=f"{C2020_OFG_BLOCK_CODE}:limited",
                    name=None,
                    cap=10,
                    codes=limited,
                )
                unlimited_block = Leaf(
                    debug_name=f"{block.debug_name} (genérico)",
                    block_code=f"{C2020_OFG_BLOCK_CODE}:unlimited",
                    name=None,
                    cap=block.cap,
                    codes=unlimited,
                )
                science_block = Leaf(
                    debug_name=f"{block.debug_name} (optativo de ciencias)",
                    block_code=f"{C2020_OFG_BLOCK_CODE}:science",
                    name=None,
                    cap=10,
                    codes=science,
                )
                block = Combination(
                    debug_name=block.debug_name,
                    block_code=f"{C2020_OFG_BLOCK_CODE}:root",
                    name=block.name,
                    cap=block.cap,
                    children=[
                        # Este orden es importante!
                        # El solver aun no soporta manejar el caso cuando ocurre
                        # "split-flow", que es cuando un curso divide su creditaje entre
                        # dos bloques.
                        # Esto *probablemente* no es legal, pero es *muy* dificil que
                        # ocurra realmente.
                        # Sin embargo, si las prioridades estan mal seteadas, puede
                        # ocurrir un caso en que el solver en su intento de optimizar
                        # cause split-flow
                        # Si estuviera `limited_block` primero, `unlimited_block`
                        # segundo y hubiera un ramo DPT de 5 creditos, se llenaria
                        # `limited_block` con el ramo DPT, y la siguiente equivalencia
                        # de 10 creditos se repartiria 5 en `limited_block` (porque
                        # quedan 5 creditos de espacio) y 5 en `unlimited_block`, porque
                        # `limited_block` tendria mas prioridad.
                        # Por ahora lo podemos arreglar invirtiendo las prioridades.
                        unlimited_block,
                        limited_block,
                        science_block,
                    ],
                )
                superblock.children[block_i] = block


def _c2020_defer_general_ofg(curriculum: Curriculum):
    # Hacer que los ramos de relleno de OFG se prefieran sobre los ramos de relleno de
    # teologico, para que no se autogenere un teologico y se tome el curso teologico
    # como OFG
    if "!L1" in curriculum.fillers:
        for filler in curriculum.fillers["!L1"]:
            filler.cost_offset -= 1


def _c2022_defer_free_area_ofg(curriculum: Curriculum):
    # Hacer que los ramos de relleno de area libre se prefieran sobre los ramos de
    # relleno de area restringida, para que no se autogenere un area restringida y se
    # tome el curso pasado como area libre
    if "!C10351" in curriculum.fillers:
        for filler in curriculum.fillers["!C10351"]:
            filler.cost_offset -= 1


COURSE_PREFIX = "courses:"
MINOR_BLOCK_CODE = f"{SUPERBLOCK_PREFIX}Minor"


def _minor_transformation(courseinfo: CourseInfo, curriculum: Curriculum):
    """
    Aplicar la "transformacion de minor".
    Los minors tienen una cierta cantidad de cursos minimos, pero si los cursos ya estan
    usados en otra parte del plan academico, se rellenan con optativos complementarios.
    Los optativos complementarios estan marcados como cursos de 0 creditos.

    Para modelar esto, duplicamos el arbol de este minor en dos copias:
    - Una de ellas tiene los optativos complementarios, pero tiene una capacidad de 50
        (o la cantidad original que sea) creditos. Es decir, tiene mas ramos que
        capacidad, por lo que no se espera que se tomen todos los optativos
        complementarios.
    - La otra tiene los cursos obligatorios de minor. No tiene los optativos
        complementarios, por lo que es necesario tomar todos los ramos del bloque.
        Este bloque esta en otra capa, de manera de no tener que "pelear" por los ramos
        con major y titulo.
    """

    # Encontrar el bloque de minor
    minor_index, minor_block = next(
        (
            (i, block)
            for i, block in enumerate(curriculum.root.children)
            if block.block_code.startswith(MINOR_BLOCK_CODE)
        ),
        (-1, None),
    )
    if minor_block is None:
        # Recordar que los planes pueden no tener minor!
        return
    if not isinstance(minor_block, Combination):
        raise Exception("minor block is a leaf?")

    # El optativo complementario es el unico ramo con cero creditos
    # Sin embargo, al cargar los datos desde SIDING los ramos con cero creditos reciben
    # 1 credito "fantasma", por lo que tenemos que buscar ramos con 1 credito
    # Encontrarlo
    filler_candidates = [block for block in minor_block.children if block.cap <= 1]
    if not filler_candidates:
        # Este minor no tiene optativos complementarios
        return
    if len(filler_candidates) > 1:
        raise Exception("more than one optativo complementario?")
    filler = filler_candidates[0]
    if not isinstance(filler, Leaf):
        raise Exception("optativo complementario is not a leaf?")

    # Eliminamos el optativo complementario del minor
    minor_block.children = [
        block for block in minor_block.children if block.block_code != filler.block_code
    ]

    # Calculamos el creditaje total de este minor
    minor_credits = sum(block.cap for block in minor_block.children)

    # Duplicar el bloque
    # Llamaremos "exhaustivo" al bloque que tiene exactamente tantos ramos como
    # capacidad tiene (pero que "comparte" sus ramos porque usa una copia de todos
    # los ramos)
    # Llamaremos "exclusivo" al bloque que tiene optativos complementarios de relleno,
    # pero que tiene que "pelear" con los otros bloques por los ramos
    exhaustive = minor_block
    exclusive = exhaustive.copy(deep=True)
    curriculum.root.children.insert(minor_index + 1, exclusive)

    # Mover el bloque exhaustivo a una capa paralela, para permitir que comparta ramos
    # con otros bloques
    _set_block_layer(exhaustive, "minor")

    # Agregamos el optativo complementario al bloque exclusivo
    # Agregamos suficientes creditos para poder completarlo a punta de optativos
    # complementarios
    exclusive.children.append(filler.copy())
    exclusive.children[-1].cap = minor_credits
    exclusive.cap = minor_credits
    exclusive.name = f"{exclusive.name} ({minor_credits} créditos exclusivos)"
    exclusive.debug_name += f" ({minor_credits} créditos exclusivos)"

    # Nos aseguramos que hayan suficientes creditos de cursos recomendados de optativo
    # complementario
    assert filler.block_code.startswith(COURSE_PREFIX)
    filler_code = filler.block_code[len(COURSE_PREFIX) :]
    filler_course = curriculum.fillers[filler_code].pop()  # Asumimos que es el ultimo
    filler_course.cost_offset += 2
    assert isinstance(filler_course.course, EquivalenceId)
    filler_credits = minor_credits
    while filler_credits > 0:
        creds = min(filler_credits, 10)
        filler_course.course = pseudocourse_with_credits(
            filler_course.course,
            creds,
        )
        curriculum.fillers[filler_code].append(filler_course.copy())
        filler_credits -= creds


TITLE_EXCLUSIVE_CREDITS = 130
TITLE_BLOCK_CODE = f"{SUPERBLOCK_PREFIX}Titulo"
OPI_CODE = "#OPI"
OPI_NAME = "Optativos de Ingeniería (OPI)"
OPI_BLOCK_CODE = f"courses:{OPI_CODE}"
OPI_EXTRAS = [
    "GOB3001",
    "GOB3004",
    "GOB3006",
    "GOB3007",
    "GOB3008",
    "GOB3009",
    "GOB3010",
    "GOB3011",
    "GOB3012",
]


async def _title_transformation(courseinfo: CourseInfo, curriculum: Curriculum):
    """
    Aplicar la "transformacion de titulo".
    Es decir, duplicar el titulo como dos bloques:
    - Uno de ellos baja el requisito de creditos a 130 y agrega OPIs, pero comparte los
        ramos con los otros bloques de la malla (llamemoslo "exclusive").
    - Otro mantiene el requisito de creditos, pero permite que los cursos cuenten para
        el titulo y otro bloque simultaneamente (llamemoslo "exhaustive").
    """

    # Encontrar el bloque de titulo
    title_index = next(
        (
            i
            for i, block in enumerate(curriculum.root.children)
            if block.block_code.startswith(TITLE_BLOCK_CODE)
        ),
        None,
    )
    if title_index is None:
        # Recordar que los planes pueden no tener titulo!
        return

    # Duplicar el bloque
    exhaustive = curriculum.root.children[title_index]
    if not isinstance(exhaustive, Combination):
        raise Exception("title block is a leaf?")
    exclusive = exhaustive.copy(deep=True)
    curriculum.root.children.insert(title_index + 1, exclusive)

    # Mover el bloque exhaustivo a una capa paralela, para permitir que comparta ramos
    # con otros bloques
    _set_block_layer(exhaustive, "title")

    # Recolectar los OPIs y armar una equivalencia ficticia
    opi_equiv = courseinfo.try_equiv(OPI_CODE)
    if opi_equiv is None:
        opis: list[str] = []
        for code, course in courseinfo.courses.items():
            if course.school != "Ingenieria" and course.school != "Ingeniería":
                continue
            # TODO: Cuales son "los cursos realizados en intercambio académico oficial
            # de la Universidad"?
            # Se supone que estos tambien cuentan para el titulo
            # TODO: Cual es la definicion exacta de un curso IPre?
            # En particular, el curso "Cmd Investigación o Proyecto Interdisciplinario"
            # cuenta como IPre?
            # TODO: Segun https://intrawww.ing.puc.cl/siding/dirdes/web_docencia/pre_grado/optativos/opt_ing_2013/alumno_2020/index.phtml,
            # existen cursos de otras facultades que se consideran como OPIs.
            # Si no hay una lista programatica en SIDING que los liste, habria que
            # incluirla textualmente.
            if (
                (len(code) >= 6 and code[3] == "3")
                or course.name == "Investigacion o Proyecto"
                or course.name == "Investigación o Proyecto"
            ):
                opis.append(code)
        opis.extend(OPI_EXTRAS)
        opi_equiv = EquivDetails(
            code=OPI_CODE,
            name=OPI_NAME,
            is_homogeneous=False,
            is_unessential=True,
            courses=opis,
        )
        await add_equivalence(opi_equiv)

    # TODO: Agregar el curso ETI188
    # "El curso ETI188 - Etica para Ingenieria se incorpora al plan de estudios como un
    # requisito necesario para obtener el titulo profesional.
    # En caso de querer realizarlo dentro de la Licenciatura este puede ser reconocido
    # como Optativo de Fundamentos o bien dentro de los creditos libres del plan de
    # formacion general."

    # Meter los codigos en un diccionario
    opi_set: set[str] = {OPI_CODE}
    ipre_set: set[str] = {OPI_CODE}
    for code in opi_equiv.courses:
        info = courseinfo.try_course(code)
        if info is None:
            continue
        # TODO: Preguntar cual es la multiplicidad de las IPres
        if (
            info.name == "Investigacion o Proyecto"
            or info.name == "Investigación o Proyecto"
        ):
            ipre_set.add(code)
        else:
            opi_set.add(code)

    # Si faltan creditos, rellenar con cursos OPI de 10 creditos
    curriculum.fillers.setdefault(OPI_CODE, []).extend(
        FillerCourse(
            course=EquivalenceId(code=OPI_CODE, credits=10),
            order=3000,  # Colocarlos al final
            cost_offset=1,  # Preferir otros ramos antes
        )
        # Rellenar con ceil(creditos_de_titulo/10) cursos
        for _i in range(_ceil_div(TITLE_EXCLUSIVE_CREDITS, 10))
    )
    exclusive.children.append(
        Combination(
            debug_name=OPI_NAME,
            block_code=f"{OPI_BLOCK_CODE}:root",
            name=OPI_NAME,
            cap=TITLE_EXCLUSIVE_CREDITS,
            children=[
                # Este orden es importante!
                # Ver el comentario sobre el orden de `limited_block` y
                # `unlimited_block` en los OFGs.
                Leaf(
                    debug_name=f"{OPI_NAME} (genérico)",
                    block_code=f"{OPI_BLOCK_CODE}:any",
                    name=None,
                    cap=TITLE_EXCLUSIVE_CREDITS,
                    codes=opi_set,
                    # cost=1,  # Preferir los ramos normales por un poquito
                ),
                Leaf(
                    debug_name=f"{OPI_NAME} (IPre)",
                    block_code=f"{OPI_BLOCK_CODE}:ipre",
                    name=None,
                    cap=20,
                    codes=ipre_set,
                    # cost=1,  # Preferir los ramos normales por un poquito
                ),
            ],
        ),
    )
    exclusive.cap = TITLE_EXCLUSIVE_CREDITS
    exclusive.name = f"{exclusive.name} ({TITLE_EXCLUSIVE_CREDITS} créditos exclusivos)"
    exclusive.debug_name += f" ({TITLE_EXCLUSIVE_CREDITS} créditos exclusivos)"


async def apply_curriculum_rules(
    courseinfo: CourseInfo,
    spec: CurriculumSpec,
    curriculum: Curriculum,
) -> Curriculum:
    _skip_extras(curriculum)
    _identify_superblocks(spec, curriculum)

    match spec.cyear.raw:
        case "C2020":
            # NOTE: El orden en que se llaman estas funciones es importante
            _merge_ofgs(curriculum)
            _allow_selection_duplication(courseinfo, curriculum)
            _limit_ofg10(courseinfo, curriculum)
            _minor_transformation(courseinfo, curriculum)
            await _title_transformation(courseinfo, curriculum)
            _c2020_defer_general_ofg(curriculum)
            # TODO: Algunos minors y titulos tienen requerimientos especiales que no son
            #   representables en el formato que provee SIDING, y por ende faltan del
            #   mock (y estan incompletos en el webservice real).
            #   Una posibilidad es por ahora hardcodear estos programas en nuestro
            #   formato (ie. hardcodearlo como `Curriculum` y no como
            #   `list[BloqueMalla]`).
            #   Tambien hay majors faltantes simplemente porque la Dipre no los ha
            #   ingresado al parecer.
            #
            #   Programas faltantes:
            #   - (M235) Major en Ingeniería, Diseño e Innovación - Track en Ingeniería
            #       Vs.02
            #   - (M143) Major en Ingeniería Física - Track Ingeniería Vs.01
            #   - (M149) Major en Ingeniería Física - Track Física Vs.01
            #   - (N242) Innovación Tecnológica Vs.01
            #   - (N290) Minor de Profundidad de Articulación Ingeniería Civil Vs.02
            #   - (N707) Minor de Profundidad de Articulación Proyectos de Diseño
            #   - (N234) Minor de Articulación Premedicina Vs.02
            #   - (N227) Minor de Profundidad Articulación Arquitectura Vs.02
            #   - (N180) Track 1: Fundamentos de Optimización Vs.02
            #   - (N181) Track 2: Fundamentos de Análisis Numérico Vs.02
            #   - (N182) Track 3: Cuantificación de Incertidumbre Vs.02
            #   - (N183) Track 4: Teoría de la Computación Vs.02
            #   - (N184) Track 5: Data Science Vs.02
            #   - (40023) Ingeniero Civil Matemático y Computacional
        case "C2022":
            # TODO: Las listas de OFG para C2022 vienen vacias desde SIDING por alguna
            #   razon.
            #   Por ahora las estamos parchando con el mock, pero hay que ver por que y
            #   que hacer al respecto.
            # TODO: Asegurarse que el area de libre eleccion no incluya las areas
            #   prohibidas.
            # TODO: Averiguar como funcionan los OFG y si requieren alguna regla
            #   especial.
            _allow_selection_duplication(courseinfo, curriculum)
            _minor_transformation(courseinfo, curriculum)
            await _title_transformation(courseinfo, curriculum)
            _c2022_defer_free_area_ofg(curriculum)
    return curriculum


FORCE_HOMOGENEOUS = (
    {"FIS1523", "ICM1003", "IIQ1003", "IIQ103H"},
    {"FIS1533", "IEE1533"},
    {"ICS1113", "ICS113H"},
)
FORCE_HOMOGENEOUS_MIN = min(len(homogeneous) for homogeneous in FORCE_HOMOGENEOUS)
FORCE_HOMOGENEOUS_MAX = max(len(homogeneous) for homogeneous in FORCE_HOMOGENEOUS)


def _fix_nonhomogeneous_equivs(courseinfo: CourseInfo, equiv: EquivDetails):
    # Algunos bloques estan definidos de forma rara
    # Por ejemplo, Termodinamica y Electricidad y Magnetismo estan definidos como una
    # lista de cursos (estilo `!C1234`) en lugar de como una equivalencia (estilo
    # `?FIS1523`).
    # Ademas, tienen nombres raros como "Minimos Major (LISTA 1)" en lugar de
    # "Termodinamica".
    # Lo parcharemos para que estas sean listas homogeneas y con el nombre correcto.
    # Tambien, parcharemos "Optimizacion" como una equivalencia homogenea
    # Colocamos un limite maximo de cursos para evitar parchar listas grandes que tengan
    # estos cursos de primero.
    if FORCE_HOMOGENEOUS_MIN <= len(equiv.courses) <= FORCE_HOMOGENEOUS_MAX and any(
        set(equiv.courses) == homogeneous for homogeneous in FORCE_HOMOGENEOUS
    ):
        equiv.is_homogeneous = True
        equiv.is_unessential = True
        info = courseinfo.try_course(equiv.courses[0])
        if info is not None:
            equiv.name = info.name


UNESSENTIAL_EQUIVS = {
    "!L1",
    "!L2",
    "!C10344",
    "!C10345",
    "!C10348",
    "!C10349",
    "!C10350",
    "!C10347",
    "!C10346",
    "!C10351",
}


def _mark_unessential_equivs(equiv: EquivDetails):
    # Hacer que los OFGs y los teologicos sean no-esenciales (ie. que no emitan un
    # error cuando no se selecciona un OFG o un teologico)
    if equiv.code in UNESSENTIAL_EQUIVS:
        equiv.is_unessential = True


def _add_c2020_science_optative_courses(equiv: EquivDetails):
    # La lista `!L1` (OFGs del curriculum C2020) no contiene los optativos de ciencias.
    # Agreguemoslos a la fuerza
    if equiv.code == "!L1":
        equiv.courses.extend(C2020_OFG_SCIENCE_OPTS)


async def apply_equivalence_rules(
    courseinfo: CourseInfo,
    equiv: EquivDetails,
) -> EquivDetails:
    """
    Modificar las equivalencias al momento de crearlas.
    Dado que las equivalencias son globales, no es posible modificarlas dependiendo de
    la version del curriculum o el programa.
    Si se quiere hacer esto, hay que separar las equivalencias en dos codigos distintos
    usando `map_equivalence_code` y luego modificar cada codigo por separado.
    Ej. `!L1` -> `!L1-C2020`, `!L1-C2022`
    """

    # Arreglar Termodinamica y Electricidad y Magnetismo
    _fix_nonhomogeneous_equivs(courseinfo, equiv)
    # Hacer que los OFGs no emitan un diagnostico de "falta desambiguar"
    _mark_unessential_equivs(equiv)
    # Agregar Optativos de Ciencias a los OFGs de C2020
    _add_c2020_science_optative_courses(equiv)

    return equiv


async def map_equivalence_code(
    courseinfo: CourseInfo,
    spec: CurriculumSpec,
    equiv_code: str,
) -> str:
    """
    Esta funcion permite cambiar los codigos de equivalencias para cada version del
    curriculum (o incluso programa) por separado, si es necesario.
    """
    return equiv_code
