from typing import Literal

from unidecode import unidecode

from app.plan.courseinfo import CourseInfo
from app.plan.validation.curriculum.tree import (
    Block,
    Combination,
    Curriculum,
    CurriculumSpec,
    Cyear,
    Leaf,
    Multiplicity,
)
from app.sync.curriculums.siding import (
    C2020_OFG_SCIENCE_OPTS,
    SidingInfo,
    translate_siding,
)
from app.sync.curriculums.storage import CurriculumStorage
from app.sync.siding.client import BloqueMalla


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


# Tabla que mapea la primera palabra del nombre textual de un bloque academico del major
# a un nombre mas machine-readable
C2020_SUPERBLOCK_TABLE = {
    "ciencias": "PlanComun",
    "base": "PlanComun",
    "formacion": "FormacionGeneral",
    "major": "Major",
}
C2022_SUPERBLOCK_TABLE = {
    "matematicas": "PlanComun",
    "fundamentos": "PlanComun",
    "formacion": "FormacionGeneral",
    "major": "Major",
}


def _map_bloqueacademico(cyear: Cyear, bloque_academico: str) -> str:
    """
    Mapear un bloque academico de SIDING en un superblock id.
    """
    # Heuristica: tomar la primera palabra, normalizarla (quitarle los tildes y todo
    # a minúscula) y buscar en una tabla hardcodeada.
    id_words = unidecode(bloque_academico).lower().split()
    if len(id_words) < 1:
        return bloque_academico
    match cyear:
        case "C2020":
            superblock_table = C2020_SUPERBLOCK_TABLE
        case "C2022":
            superblock_table = C2022_SUPERBLOCK_TABLE
    return superblock_table.get(id_words[0], bloque_academico)


def _identify_superblocks(spec: CurriculumSpec, block: Block):
    """
    Cambia los codigos de los bloques academicos a nombres "machine readable".
    Por ejemplo, cambia "Ingeniero Civil en Computación" a 'title'
    """

    if isinstance(block, Combination):
        for subblock in block.children:
            _identify_superblocks(spec, subblock)
    else:
        block.superblock = _map_bloqueacademico(spec.cyear, block.superblock)


# Identifica si un bloque es OFG de C2020.
def _is_c2020_ofg(block: Block) -> bool:
    if isinstance(block, Combination):
        return any(_is_c2020_ofg(child) for child in block.children)
    return block.list_code.endswith("L1")


def _merge_c2020_ofgs(curriculum: Curriculum):
    # Junta los bloques de OFG de 10 creditos en un bloque grande de OFG
    for superblock in curriculum.root.children:
        if not isinstance(superblock, Combination):
            continue
        # Junta todos los bloques que son OFG en una lista
        l1_blocks: list[Leaf] = [
            block
            for block in superblock.children
            if isinstance(block, Leaf) and _is_c2020_ofg(block)
        ]
        if len(l1_blocks) > 0:
            # Elimina todos los bloques que son OFG de `superblock.children`
            superblock.children = [
                block for block in superblock.children if not _is_c2020_ofg(block)
            ]
            # Juntar todos los bloques OFG en un bloque y agregarlo de vuelta
            total_cap = sum(block.cap for block in l1_blocks)
            superblock.children.append(
                Leaf(
                    debug_name=l1_blocks[0].debug_name,
                    name=l1_blocks[0].name,
                    superblock=l1_blocks[0].superblock,
                    cap=total_cap,
                    list_code=l1_blocks[0].list_code,
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
            if isinstance(block, Leaf) and _is_c2020_ofg(block):
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
                            group={code},
                            credits=2 * info.credits,
                        )
                # Only do it once
                return


def _ofg_classify(
    courseinfo: CourseInfo,
    code: str,
) -> Literal["limited"] | Literal["unlimited"] | Literal["science"]:
    info = courseinfo.try_course(code)
    if info is None:
        return "unlimited"
    if info.code in C2020_OFG_SCIENCE_OPTS:
        return "science"
    if info.credits != 5:
        return "unlimited"
    if info.code.startswith(("DPT", "RII", "CAR")) or info.code in (
        "MEB158",
        "MEB166",
        "MEB174",
    ):
        return "limited"
    return "unlimited"


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
    # Los ramos de esta lista no son parte de la lista `L1` que brinda
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
            if isinstance(block, Leaf) and _is_c2020_ofg(block):
                # Segregar los cursos de 5 creditos que cumplan los requisitos
                limited: set[str] = set()
                unlimited: set[str] = set()
                science: set[str] = set()
                for code in block.codes:
                    match _ofg_classify(courseinfo, code):
                        case "unlimited":
                            unlimited.add(code)
                        case "limited":
                            limited.add(code)
                        case "science":
                            science.add(code)
                # Separar el bloque en 3
                limited_block = Leaf(
                    debug_name=f"{block.debug_name} (máx. 10 creds. DPT y otros)",
                    name=None,
                    superblock=block.superblock,
                    cap=10,
                    list_code=block.list_code,
                    codes=limited,
                )
                unlimited_block = Leaf(
                    debug_name=f"{block.debug_name} (genérico)",
                    name=None,
                    superblock=block.superblock,
                    cap=block.cap,
                    list_code=block.list_code,
                    codes=unlimited,
                )
                science_block = Leaf(
                    debug_name=f"{block.debug_name} (optativo de ciencias)",
                    name=None,
                    superblock=block.superblock,
                    cap=10,
                    list_code=block.list_code,
                    codes=science,
                )
                block = Combination(
                    debug_name=block.debug_name,
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
    for filler_code, fillers in curriculum.fillers.items():
        if filler_code.endswith("L1"):
            for filler in fillers:
                filler.cost_offset -= 1


def _c2022_defer_free_area_ofg(curriculum: Curriculum):
    # Hacer que los ramos de relleno de area libre se prefieran sobre los ramos de
    # relleno de area restringida, para que no se autogenere un area restringida y se
    # tome el curso pasado como area libre
    for filler_code, fillers in curriculum.fillers.items():
        if filler_code.endswith("C10351"):
            for filler in fillers:
                filler.cost_offset -= 1


def patch_major(
    courseinfo: CourseInfo,
    spec: CurriculumSpec,
    curr: Curriculum,
) -> Curriculum:
    """
    Aplicar reglas del plan comun y el major.
    """

    _skip_extras(curr)
    _identify_superblocks(spec, curr.root)

    match spec.cyear:
        case "C2020":
            # NOTE: El orden en que se llama a estas funciones es importante
            _merge_c2020_ofgs(curr)
            _limit_ofg10(courseinfo, curr)
            _c2020_defer_general_ofg(curr)
            _allow_selection_duplication(courseinfo, curr)
        case "C2022":
            # TODO: Averiguar bien como funcionan los OFG y si falta alguna regla
            # especial.
            _c2022_defer_free_area_ofg(curr)
            _allow_selection_duplication(courseinfo, curr)

    # TODO: Marcar termodinamica, electromagnetismo y optimizacion como equivalencias
    # homogeneas.
    # TODO: Marcar los OFGs y los teologicos como equivalencias no esenciales.

    return curr


def translate_major(
    courseinfo: CourseInfo,
    out: CurriculumStorage,
    spec: CurriculumSpec,
    siding: SidingInfo,
    raw_blocks: list[BloqueMalla],
):
    # Un identificador que identifique a los majors únicamente
    spec_id = "MAJOR"

    # Traducir la malla de SIDING en un curriculum nativo pero incompleto
    curr = translate_siding(courseinfo, out, spec_id, siding, raw_blocks)

    # Completar los detalles faltantes
    curr = patch_major(courseinfo, spec, curr)

    # Agregar al set de curriculums
    out.set_major(spec, curr)


# La malla de plan comun se construye a partir de la malla de este major (computacion)
PLANCOMUN_BASE_MAJOR = "M245"
# La malla de plan comun se construye filtrando estos bloques de la malla de algun major
PLANCOMUN_SUPERBLOCKS = {"PlanComun", "FormacionGeneral"}


def translate_common_plan(
    courseinfo: CourseInfo,
    out: CurriculumStorage,
    siding: SidingInfo,
):
    """
    Generar el plan comun.
    Para esto se toma algun major arbitrario (por ahora computacion) y se eliminan los
    ramos especificos de major.
    """

    # Generar un plan comun para cada version del curriculum
    for cyear, mallas in siding.plans.items():
        if PLANCOMUN_BASE_MAJOR not in mallas.plans:
            raise Exception(
                f"major {PLANCOMUN_BASE_MAJOR} (the base for plancomun)"
                f" not found for cyear {cyear}",
            )
        # Filtrar por bloque academico
        filtered_blocks = [
            block
            for block in mallas.plans[PLANCOMUN_BASE_MAJOR]
            if _map_bloqueacademico(cyear, block.BloqueAcademico or "")
            in PLANCOMUN_SUPERBLOCKS
        ]
        # Traducir como un major cualquiera, pero sin un major particular
        translate_major(
            courseinfo,
            out,
            CurriculumSpec(cyear=cyear, major=None, minor=None, title=None),
            siding,
            filtered_blocks,
        )
