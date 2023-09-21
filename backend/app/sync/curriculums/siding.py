import logging
from collections import defaultdict

from pydantic import BaseModel, Field
from unidecode import unidecode

from app.plan.course import ConcreteId, EquivalenceId
from app.plan.courseinfo import CourseInfo, EquivDetails
from app.plan.validation.curriculum.tree import (
    SUPERBLOCK_PREFIX,
    Block,
    Combination,
    Curriculum,
    Cyear,
    FillerCourse,
    Leaf,
)
from app.sync.curriculums.storage import CurriculumStorage
from app.sync.siding import client as siding_client
from app.sync.siding.client import (
    BloqueMalla,
    Curso,
    Major,
    Minor,
    PlanEstudios,
    StringArray,
    Titulo,
)

IGNORE_CYEARS_BEFORE = "C2020"


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


log = logging.getLogger("plan-collator")


class MallasPorCodigo(BaseModel):
    """
    Contiene un mapeo de codigo de programa (ie. M230, N177) a una lista de bloques.
    """

    plans: dict[str, list[BloqueMalla]] = Field(default_factory=dict)


class SidingInfo(BaseModel):
    majors: list[Major]
    minors: list[Minor]
    titles: list[Titulo]
    plans: defaultdict[Cyear, MallasPorCodigo] = Field(
        default_factory=lambda: defaultdict(MallasPorCodigo),
    )
    lists: dict[str, list[Curso]]


async def fetch_siding(courseinfo: CourseInfo) -> SidingInfo:
    # Fetch major/minor/title offer
    siding = SidingInfo(
        majors=await siding_client.get_majors(),
        minors=await siding_client.get_minors(),
        titles=await siding_client.get_titles(),
        lists={},
    )

    # Filter cyears that are not interesting for us
    siding.majors = list(
        filter(lambda m: filter_relevant_cyears(m.Curriculum), siding.majors),
    )
    siding.minors = list(
        filter(lambda m: filter_relevant_cyears(m.Curriculum), siding.minors),
    )
    siding.titles = list(
        filter(lambda m: filter_relevant_cyears(m.Curriculum), siding.titles),
    )

    # Fetch plans
    await fetch_siding_plans(siding)

    # Fetch predefined lists
    await fetch_siding_lists(courseinfo, siding)

    # Currently, SIDING returns empty lists for C2022 OFGs
    # Fill in these lists "manually"
    # TODO: Remove this hack once SIDING fixes this
    fill_in_c2022_ofgs(courseinfo, siding)

    # Currently, SIDING does not include the science optatives in their C2020 OFG list
    # Patch this
    fill_in_c2020_science_ofg(courseinfo, siding)

    return siding


def filter_relevant_cyears(cyears: StringArray | None) -> bool:
    if cyears is None:
        return False
    cyears.strings.string = list(
        filter(lambda cyear: cyear >= IGNORE_CYEARS_BEFORE, cyears.strings.string),
    )
    return len(cyears.strings.string) > 0


async def fetch_siding_plans(siding: SidingInfo):
    # Fetch majors in offer
    for major in siding.majors:
        if major.Curriculum is None:
            continue
        for cyear_str in major.Curriculum.strings.string:
            cyear = Cyear.from_str(cyear_str)
            if cyear is None:
                log.error(
                    "el major %s tiene version de curriculum %s que no esta soportada",
                    major.CodMajor,
                    cyear_str,
                )
                continue
            siding.plans[cyear].plans[
                major.CodMajor
            ] = await siding_client.get_curriculum_for_spec(
                PlanEstudios(
                    CodCurriculum=cyear_str,
                    CodMajor=major.CodMajor,
                    CodMinor="N",
                    CodTitulo="",
                ),
            )
    # Fetch minors in offer
    for minor in siding.minors:
        if minor.Curriculum is None:
            continue
        for cyear_str in minor.Curriculum.strings.string:
            cyear = Cyear.from_str(cyear_str)
            if cyear is None:
                log.error(
                    "el minor %s tiene version de curriculum %s que no esta soportada",
                    minor.CodMinor,
                    cyear_str,
                )
                continue
            siding.plans[cyear].plans[
                minor.CodMinor
            ] = await siding_client.get_curriculum_for_spec(
                PlanEstudios(
                    CodCurriculum=cyear_str,
                    CodMajor="M",
                    CodMinor=minor.CodMinor,
                    CodTitulo="",
                ),
            )
    # Fetch titles in offer
    for title in siding.titles:
        if title.Curriculum is None:
            continue
        for cyear_str in title.Curriculum.strings.string:
            cyear = Cyear.from_str(cyear_str)
            if cyear is None:
                log.error(
                    "el titulo %s tiene version de curriculum %s que no esta soportada",
                    title.CodTitulo,
                    cyear_str,
                )
                continue
            siding.plans[cyear].plans[
                title.CodTitulo
            ] = await siding_client.get_curriculum_for_spec(
                PlanEstudios(
                    CodCurriculum=cyear_str,
                    CodMajor="M",
                    CodMinor="N",
                    CodTitulo=title.CodTitulo,
                ),
            )


async def fetch_siding_lists(courseinfo: CourseInfo, siding: SidingInfo):
    # Collect predefined lists
    predefined_lists: set[str] = set()
    for _cyear, plans in siding.plans.items():
        for _plan_code, plan in plans.plans.items():
            for block in plan:
                if block.CodLista:
                    predefined_lists.add(block.CodLista)

    # Fetch predefined lists
    for lcode in predefined_lists:
        siding.lists[lcode] = await siding_client.get_predefined_list(lcode)


def translate_siding(
    courseinfo: CourseInfo,
    out: CurriculumStorage,
    siding: SidingInfo,
    raw_blocks: list[BloqueMalla],
) -> Curriculum:
    """
    Translates a SIDING list of blocks as-is directly into a curriculum tree.
    Does not consider any implicit rules, these should be applied afterwards depending
    on the context.

    The returned curriculum tree has some `-1` capacities.
    Nodes with -1 capacity actually have "infinite" capacity (ie. the total capacity of
    their children).
    This should be fixed afterwards with `Curriculum.freeze_capacities`.

    Any found lists will be added to `out`.
    """

    curriculum = Curriculum.empty()
    curriculum.root.cap = -1

    # Group into superblocks
    superblocks: dict[str, list[Block]] = {}
    for raw_block in raw_blocks:
        if raw_block.CodSigla is not None and raw_block.Equivalencias is None:
            # Concrete course
            code = raw_block.CodSigla
            recommended = ConcreteId(code=code)
            codes = [code]
        else:
            # Equivalence
            is_homogeneous = False
            if raw_block.CodLista is not None:
                # List equivalence
                code = f"!{raw_block.CodLista}"
                cursos = siding.lists.get(raw_block.CodLista)
                if cursos is None:
                    raise Exception(f"unknown SIDING list code {raw_block.CodLista}")
                codes: list[str] = []
                for curso in cursos:
                    if curso.Sigla is None:
                        continue
                    if courseinfo.try_course(curso.Sigla) is None:
                        log.warning(
                            f"unknown course {curso.Sigla}"
                            f" in SIDING list {raw_block.CodLista}",
                        )
                        continue
                    codes.append(curso.Sigla)
            elif raw_block.CodSigla is not None and raw_block.Equivalencias is not None:
                code = f"?{raw_block.CodSigla}"
                codes = [raw_block.CodSigla]
                for curso in raw_block.Equivalencias.Cursos:
                    if curso.Sigla is not None:
                        codes.append(curso.Sigla)
                is_homogeneous = True
            else:
                raise Exception("siding api returned invalid curriculum block")
            if len(codes) == 1:
                # Just a single course
                code = codes[0]
                recommended = ConcreteId(code=code)
            else:
                # Add equivalence to global list of equivalences
                if code not in out.lists:
                    out.lists[code] = EquivDetails(
                        code=code,
                        name=raw_block.Nombre,
                        is_homogeneous=is_homogeneous,
                        is_unessential=False,
                        courses=codes,
                    )
                # Accept the equivalence code itself
                codes.append(code)
                # Create filler course
                recommended = EquivalenceId(code=code, credits=raw_block.Creditos)
        # 0-credit courses get a single ghost credit
        creds = 1 if raw_block.Creditos == 0 else raw_block.Creditos
        recommended_order = raw_block.SemestreBloque * 10 + raw_block.OrdenSemestre
        superblock = superblocks.setdefault(raw_block.BloqueAcademico or "", [])
        superblock.append(
            Leaf(
                debug_name=raw_block.Nombre,
                block_code=f"courses:{code}",
                name=raw_block.Nombre,
                cap=creds,
                codes=set(codes),
            ),
        )
        curriculum.fillers.setdefault(recommended.code, []).append(
            FillerCourse(course=recommended, order=recommended_order),
        )

    # Transform into a somewhat valid curriculum
    for superblock_name, leaves in superblocks.items():
        curriculum.root.children.append(
            Combination(
                debug_name=superblock_name,
                block_code=f"{SUPERBLOCK_PREFIX}{superblock_name}",
                name=superblock_name,
                cap=-1,
                children=leaves,
            ),
        )

    return curriculum


C2022_OFG_AREA_LISTS = {
    "C10344": "Formación Filosófica",
    "C10345": "Formación Teológica",
    "C10348": "Ecología Integral y Sustentabilidad",
    "C10349": "Humanidades",
    "C10350": "Salud y Bienestar",
    "C10347": "Ciencias Sociales",
    "C10346": "Arte",
    "C10351": "",
}


def fill_in_c2022_ofgs(courseinfo: CourseInfo, siding: SidingInfo):
    """
    Las listas de OFG para C2022 vienen vacias desde SIDING.
    Por ahora, llenarlas manualmente a partir de la informacion de buscacursos.
    """

    # Agrupar los cursos por area
    by_area: dict[str, list[str]] = {}
    for course in courseinfo.courses.values():
        if course.area is not None:
            by_area.setdefault(course.area, []).append(course.code)

    # Llenar las listas con los cursos correspondientes
    for lcode, keyphrase in C2022_OFG_AREA_LISTS.items():
        assert lcode in siding.lists
        if siding.lists[lcode]:
            log.warning(
                "patching C2022 OFG list %s, but it is actually not empty",
                lcode,
            )
        keywords = [unidecode(word).lower() for word in keyphrase.split(" ") if word]
        for areaname, areacodes in by_area.items():
            areawords = [
                unidecode(word).lower() for word in areaname.split(" ") if word
            ]
            if all(
                any(areaword[:3] == keyword[:3] for areaword in areawords)
                for keyword in keywords
            ):
                siding.lists[lcode].extend(
                    Curso(Sigla=code, Nombre=None, Semestralidad=None, Creditos=None)
                    for code in areacodes
                )


def fill_in_c2020_science_ofg(courseinfo: CourseInfo, siding: SidingInfo):
    """
    La lista de OFGs para C2020, que se llama L1 en SIDING, no contiene los optativos de
    ciencias.
    Parcharla.
    """

    ofg_courses = siding.lists["L1"]
    ofg_courses.extend(
        Curso(Sigla=code, Nombre=None, Semestralidad=None, Creditos=None)
        for code in C2020_OFG_SCIENCE_OPTS
    )
