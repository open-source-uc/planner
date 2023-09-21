from app.plan.course import EquivalenceId
from app.plan.courseinfo import CourseDetails, CourseInfo, EquivDetails
from app.plan.validation.curriculum.tree import (
    Combination,
    Curriculum,
    CurriculumSpec,
    FillerCourse,
    Leaf,
    cyear_from_str,
)
from app.sync.curriculums.scrape.minor import ScrapedProgram
from app.sync.curriculums.scrape.translate import ProgramType, translate_scrape
from app.sync.curriculums.siding import SidingInfo
from app.sync.curriculums.storage import CurriculumStorage, ProgramDetails
from app.sync.siding.client import BloqueMalla, decode_cyears

TITLE_EXCLUSIVE_CREDITS = 130
TITLE_TYPE = ProgramType(
    superblock_id="Titulo",
    readable_id="Título",
    layer_id="title",
    order_base=200,
    exclusive_credits=TITLE_EXCLUSIVE_CREDITS,
)


def translate_title(
    courseinfo: CourseInfo,
    out: CurriculumStorage,
    spec: CurriculumSpec,
    meta: ProgramDetails,
    siding: list[BloqueMalla],
    scrape: ScrapedProgram,
):
    # TODO: Agregar el curso ETI188
    # "El curso ETI188 - Etica para Ingenieria se incorpora al plan de estudios como un
    # requisito necesario para obtener el titulo profesional.
    # En caso de querer realizarlo dentro de la Licenciatura este puede ser reconocido
    # como Optativo de Fundamentos o bien dentro de los creditos libres del plan de
    # formacion general."

    # Traducir desde los datos scrapeados
    curr = translate_scrape(
        TITLE_TYPE,
        courseinfo,
        out,
        spec,
        meta.name,
        siding,
        scrape,
    )

    # Agregar los OPIs a mano
    add_opi_to_title(courseinfo, out, spec, curr)

    # Agregar el titulo al listado
    out.set_title(spec, curr)


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


def add_opi_to_title(
    courseinfo: CourseInfo,
    out: CurriculumStorage,
    spec: CurriculumSpec,
    curr: Curriculum,
):
    # Encontrar el bloque exclusivo de titulo
    exclusive_block = next(
        (block for block in curr.root.children if block.cap == TITLE_EXCLUSIVE_CREDITS),
        None,
    )
    if exclusive_block is None:
        raise Exception(f"couldn't find exclusive block for title {spec}")
    assert isinstance(exclusive_block, Combination)

    # Conseguir la equivalencia de OPIs
    opi_equiv = build_opi_equiv(courseinfo, out)

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

    # Agregar los OPIs a los requerimientos del bloque exclusivo
    exclusive_block.children.append(
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

    # Agregar los OPIs en cursos de 10 creditos, hasta completar los 130
    curr.fillers.setdefault(OPI_CODE, []).extend(
        FillerCourse(
            course=EquivalenceId(code=OPI_CODE, credits=10),
            order=3000,  # Colocarlos al final
            cost_offset=1,  # Preferir otros ramos antes
        )
        # Rellenar con ceil(creditos_de_titulo/10) cursos
        for _i in range(_ceil_div(TITLE_EXCLUSIVE_CREDITS, 10))
    )


def build_opi_equiv(courseinfo: CourseInfo, out: CurriculumStorage) -> EquivDetails:
    # Reusar la equivalencia de OPIs si se puede
    if OPI_CODE in out.lists:
        return out.lists[OPI_CODE]

    # Sino, recolectar los cursos que calzan con los requisitos
    opis = [course.code for course in courseinfo.courses.values() if is_opi(course)]
    opis.extend(OPI_EXTRAS)
    opi_equiv = EquivDetails(
        code=OPI_CODE,
        name=OPI_NAME,
        is_homogeneous=False,
        is_unessential=True,
        courses=opis,
    )

    # Almacenar la equivalencia para reusarla en otros planes
    out.lists[OPI_CODE] = opi_equiv
    return opi_equiv


def is_opi(course: CourseDetails) -> bool:
    if course.school != "Ingenieria" and course.school != "Ingeniería":
        return False
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
    return (
        (len(course.code) >= 6 and course.code[3] == "3")
        or course.name == "Investigacion o Proyecto"
        or course.name == "Investigación o Proyecto"
    )


def _ceil_div(a: int, b: int) -> int:
    """
    Compute `ceil(a / b)` without floating-point error.
    """
    return -(a // -b)


def add_manual_title_offer(siding: SidingInfo, out: CurriculumStorage):
    """
    El título 40072 esta realmente dividido en 3, y por ende Planner lo separa en 3.
    Sin embargo, SIDING no hace esto, por lo que hay que hacerlo a mano.
    """

    special_code = "40072"
    areas = [
        "Área 1: Ingeniería de Procesos",
        "Área 2: Tecnología Ambiental",
        "Área 3: Biotecnología",
    ]

    special = next(title for title in siding.titles if title.CodTitulo == special_code)
    for cyear_str in decode_cyears(special.Curriculum):
        cyear = cyear_from_str(cyear_str)
        assert cyear is not None
        for i, areaname in enumerate(areas):
            out.offer[cyear].title[f"{special_code}-{i+1}"] = ProgramDetails(
                code=f"{special_code}-{i+1}",
                name=f"{special.Nombre} - {areaname}",
                version=special.VersionTitulo or "",
                program_type=special.TipoTitulo,
            )
