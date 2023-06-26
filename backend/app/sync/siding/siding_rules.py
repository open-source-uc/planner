"""
En este archivo se concentran las transformaciones sobre las mallas que debemos hacer,
pero que no estan especificadas por SIDING de forma computer-readable, y por ende
tenemos que implementar en Python.

Como este codigo es especifico a SIDING y probablemente tenga que ser tocado por otra
gente en un futuro, los comentarios estan en español al contrario del resto del codigo.

Cuando aparezca una nueva version del curriculum con reglas especificas, este codigo es
el que habra que tocar.
"""


from ...plan.course import EquivalenceId
from ...plan.courseinfo import CourseInfo, EquivDetails, add_equivalence
from ...plan.validation.curriculum.tree import (
    Block,
    Combination,
    Curriculum,
    CurriculumSpec,
    FillerCourse,
    Leaf,
)


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


def _is_ofg(block: Block) -> bool:
    """
    Check if the given block is an OFG block or not.
    """
    return isinstance(block, Leaf) and next(iter(block.codes.keys()), None) == "!L1"


def _merge_ofgs(curriculum: Curriculum):
    # Junta los bloques de OFG de 10 creditos en un bloque grande de OFG
    # El codigo de lista para los OFG es `!L1`
    for superblock in curriculum.root.children:
        if not isinstance(superblock, Combination):
            continue
        l1_blocks: list[Leaf] = []
        for block in superblock.children:
            if not isinstance(block, Leaf):
                continue
            if _is_ofg(block):
                l1_blocks.append(block)
        if len(l1_blocks) > 0:
            superblock.children = [
                block for block in superblock.children if not _is_ofg(block)
            ]
            total_cap = sum(block.cap for block in l1_blocks)
            fill_with: list[FillerCourse] = []
            for block in l1_blocks:
                fill_with.extend(block.fill_with)
            fill_with.sort(key=lambda rec: rec.order, reverse=True)
            superblock.children.append(
                Leaf(
                    debug_name=l1_blocks[0].debug_name,
                    name=l1_blocks[0].name,
                    cap=total_cap,
                    fill_with=fill_with,
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
            if isinstance(block, Leaf) and _is_ofg(block):
                for code in block.codes:
                    if not code.startswith("DPT"):
                        continue
                    info = courseinfo.try_course(code)
                    if info is None:
                        continue
                    if info.name.startswith("Seleccion ") or info.name.startswith(
                        "Selección ",
                    ):
                        block.codes[code] = 2


def _limit_ofg10(courseinfo: CourseInfo, curriculum: Curriculum):
    # https://intrawww.ing.puc.cl/siding/dirdes/web_docencia/pre_grado/formacion_gral/alumno_2020/index.phtml
    # En el bloque de OFG hay algunos cursos de 5 creditos que en conjunto pueden
    # contribuir a lo mas 10 creditos:
    # - DPT (deportivos)
    # - RII (inglés)
    # - CAR (CARA)
    # - OFG plan antiguo (MEB158, MEB166 y MEB174)

    def is_limited(courseinfo: CourseInfo, code: str):
        info = courseinfo.try_course(code)
        if info is None:
            return False
        if info.credits != 5:
            return False
        return (
            code.startswith(("DPT", "RII", "CAR"))
            or code == "MEB158"
            or code == "MEB166"
            or code == "MEB174"
        )

    for superblock in curriculum.root.children:
        if not isinstance(superblock, Combination):
            continue
        for block_i, block in enumerate(superblock.children):
            if isinstance(block, Leaf) and _is_ofg(block):
                # Segregar los cursos de 5 creditos que cumplan los requisitos
                limited = {}
                unlimited = {}
                for code, mult in block.codes.items():
                    if is_limited(courseinfo, code):
                        limited[code] = mult
                    else:
                        unlimited[code] = mult
                # Separar el bloque en 2
                limited_block = Leaf(
                    debug_name=f"{block.debug_name} (máx. 10 creds. DPT y otros)",
                    name=None,
                    cap=10,
                    codes=limited,
                )
                unlimited_block = Leaf(
                    debug_name=f"{block.debug_name} (genérico)",
                    name=None,
                    cap=block.cap,
                    codes=unlimited,
                    fill_with=block.fill_with,
                )
                block = Combination(
                    debug_name=block.debug_name,
                    name=block.name,
                    cap=block.cap,
                    children=[
                        limited_block,
                        unlimited_block,
                    ],
                )
                superblock.children[block_i] = block


async def _title_transformation(courseinfo: CourseInfo, curriculum: Curriculum):
    """
    Aplicar la "transformacion de titulo".
    Es decir, duplicar el titulo como dos bloques:
    - Uno de ellos baja el requisito de creditos a 130 y agrega OPIs, pero comparte los
        ramos con los otros bloques de la malla (llamemoslo "exclusive").
    - Otro mantiene el requisito de creditos, pero permite que los cursos cuenten para
        el titulo y otro bloque simultaneamente (llamemoslo "exhaustive").
    """

    opi_code = "#OPI"
    opi_name = "Optativos de Ingeniería (OPI)"
    title_exclusive_creds = 130

    # Encontrar el bloque de titulo
    title_index = None
    for i, block in enumerate(curriculum.root.children):
        if block.name is not None and block.name.startswith("Ingeniero"):
            title_index = i
            break
    if title_index is None:
        return

    # Duplicar el bloque
    exhaustive = curriculum.root.children[title_index]
    if not isinstance(exhaustive, Combination):
        return
    exclusive = exhaustive.copy(deep=True)
    curriculum.root.children.insert(title_index + 1, exclusive)

    # Mover el bloque exhaustivo a una capa paralela, para permitir que comparta ramos
    # con otros bloques
    def set_layer(block: Block):
        if isinstance(block, Leaf):
            block.layer = "title"
        else:
            for subblock in block.children:
                set_layer(subblock)

    set_layer(exhaustive)

    # Recolectar los OPIs y armar una equivalencia ficticia
    opi_equiv = courseinfo.try_equiv(opi_code)
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
            if (
                (len(code) >= 6 and code[3] == "3")
                or course.name == "Investigacion o Proyecto"
                or course.name == "Investigación o Proyecto"
            ):
                opis.append(code)
        opi_equiv = EquivDetails(
            code=opi_code,
            name=opi_name,
            is_homogeneous=False,
            is_unessential=True,
            courses=opis,
        )
        await add_equivalence(opi_equiv)

    # Meter los codigos en un diccionario
    opi_dict: dict[str, int | None] = {opi_code: None}
    ipre_dict: dict[str, int | None] = {}
    for code in opi_equiv.courses:
        info = courseinfo.try_course(code)
        if info is None:
            continue
        if (
            info.name == "Investigacion o Proyecto"
            or info.name == "Investigación o Proyecto"
        ):
            ipre_dict[code] = 1
        else:
            opi_dict[code] = 1

    # Agregar OPIs y reducir el limite de creditos al exclusivo
    fill_with: list[FillerCourse] = [
        FillerCourse(
            course=EquivalenceId(code=opi_code, credits=10),
            order=1000,
            cost=1,
        )
        for _i in range((title_exclusive_creds + 9) // 10)
    ]
    exclusive.children.append(
        Combination(
            debug_name=opi_name,
            name=opi_name,
            cap=title_exclusive_creds,
            children=[
                Leaf(
                    debug_name=f"{opi_name} (genérico)",
                    name=None,
                    cap=title_exclusive_creds,
                    codes=opi_dict,
                    fill_with=fill_with,
                ),
                Leaf(
                    debug_name=f"{opi_name} (IPre)",
                    name=None,
                    cap=20,
                    codes=ipre_dict,
                ),
            ],
        ),
    )
    exclusive.cap = title_exclusive_creds
    exclusive.name = f"{exclusive.name} (130 créditos exclusivos)"


async def apply_curriculum_rules(
    courseinfo: CourseInfo,
    spec: CurriculumSpec,
    curriculum: Curriculum,
) -> Curriculum:
    _skip_extras(curriculum)

    match spec.cyear.raw:
        case "C2020":
            # NOTE: El orden en que se llaman estas funciones es importante
            _merge_ofgs(curriculum)
            _allow_selection_duplication(courseinfo, curriculum)
            _limit_ofg10(courseinfo, curriculum)
            await _title_transformation(courseinfo, curriculum)
            # TODO: Agregar optativo de ciencias
            #   Se pueden tomar hasta 10 creditos de optativo de ciencias, que es una
            #   lista separada que al parecer solo esta disponible en forma textual.
            #   Los ramos de esta lista no son parte de la lista `!L1` que brinda
            #   SIDING, y tampoco sabemos si esta disponible en otra lista.
            #   La lista L3 se ve prometedora, incluso incluye un curso "ING0001
            #   Optativo En Ciencias" generico, pero no es exactamente igual al listado
            #   textual en SIDING.
            #   Referencias:
            #   "Además, es válido para avance curricular de OFG máximo 1 curso
            #   optativo en ciencias (10 cr.) de una lista de cursos Optativos de
            #   Ciencia, o su equivalente, definida por el Comité Curricular de la
            #   Escuela de Ingeniería."
            #   https://intrawww.ing.puc.cl/siding/dirdes/web_docencia/pre_grado/optativos/op_ciencias/alumno_2020/index.phtml
            #   https://intrawww.ing.puc.cl/siding/dirdes/web_docencia/pre_grado/formacion_gral/alumno_2020/index.phtml
            # TODO: Asegurarse que los optativos complementarios de minor funcionen
            #   correctamente.
            pass
    return curriculum


def _fix_nonhomogeneous_equivs(courseinfo: CourseInfo, equiv: EquivDetails):
    # Algunos bloques estan definidos de forma rara
    # Por ejemplo, Termodinamica y Electricidad y Magnetismo estan definidos como una
    # lista de cursos (estilo `!C1234`) en lugar de como una equivalencia (estilo
    # `?FIS1523`).
    # Ademas, tienen nombres raros como "Minimos Major (LISTA 1)" en lugar de
    # "Termodinamica".
    # Lo parcharemos para que estas sean listas homogeneas y con el nombre correcto.
    # Tambien, parcharemos "Optimizacion" como una equivalencia homogenea
    if ("(LISTA " in equiv.name and ")" in equiv.name) or (
        len(equiv.courses) >= 1 and equiv.courses[0] == "ICS1113"
    ):
        equiv.is_homogeneous = True
        equiv.is_unessential = True
        if len(equiv.courses) >= 1:
            info = courseinfo.try_course(equiv.courses[0])
            if info is not None:
                equiv.name = info.name


def _mark_unessential_equivs(equiv: EquivDetails):
    # Hacer que los OFGs y los teologicos sean no-esenciales (ie. que no emitan un
    # error cuando no se selecciona un OFG o un teologico)
    if equiv.code == "!L1" or equiv.code == "!L2":
        equiv.is_unessential = True


async def apply_equivalence_rules(
    courseinfo: CourseInfo,
    spec: CurriculumSpec,
    equiv: EquivDetails,
) -> EquivDetails:
    # Arreglar Termodinamica y Electricidad y Magnetismo
    _fix_nonhomogeneous_equivs(courseinfo, equiv)
    # Hacer que los OFGs no emitan un diagnostico de "falta desambiguar"
    _mark_unessential_equivs(equiv)

    return equiv
