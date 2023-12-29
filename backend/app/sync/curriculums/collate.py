"""
Collates information from various sources to build a complete curriculum plan
specification.
"""

import logging
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from itertools import chain

from pydantic import BaseModel

from app.plan.course import ConcreteId, EquivalenceId
from app.plan.courseinfo import CourseDetails
from app.plan.validation.curriculum.tree import (
    Block,
    CurriculumSpec,
    Cyear,
    FillerCourse,
    Leaf,
    MajorCode,
    MinorCode,
    Multiplicity,
    TitleCode,
    cyear_from_str,
)
from app.sync.curriculums.bypass import Bypass
from app.sync.curriculums.major import (
    translate_common_plan,
    translate_major,
)
from app.sync.curriculums.minor import translate_minor
from app.sync.curriculums.scrape.common import ScrapedProgram
from app.sync.curriculums.scrape.major import scrape_majors
from app.sync.curriculums.scrape.minor import scrape_minors
from app.sync.curriculums.scrape.title import scrape_titles
from app.sync.curriculums.siding import SidingInfo, fetch_siding
from app.sync.curriculums.storage import CurriculumStorage, ProgramDetails, ProgramOffer
from app.sync.curriculums.title import add_manual_title_offer, translate_title
from app.sync.siding.client import (
    BloqueMalla,
    Major,
    Minor,
    Titulo,
    decode_cyears,
)

log = logging.getLogger("plan-collator")


class BypassProgram(BaseModel):
    major: MajorCode | None = None
    minor: MinorCode | None = None
    title: TitleCode | None = None
    plan: Bypass


class BypassInfo(BaseModel):
    majors: list[BypassProgram]
    minors: list[BypassProgram]
    titles: list[BypassProgram]


class ScrapedInfo(BaseModel):
    majors: set[MajorCode]
    minors: dict[MinorCode, list[ScrapedProgram]]
    titles: dict[TitleCode, ScrapedProgram]


async def collate_plans(courses: dict[str, CourseDetails]) -> CurriculumStorage:
    # Scrape information from PDFs
    scraped = ScrapedInfo(
        majors=scrape_majors(),
        minors=scrape_minors(courses),
        titles=scrape_titles(courses),
    )

    # Fetch information from SIDING
    siding = await fetch_siding(courses)

    # Algunos titulos se agregan manualmente
    add_manual_title_offer(siding)

    # Cargar los planes que se agregan manualmente
    bypass = load_bypass(courses, scraped, siding)

    # Colocar los curriculums resultantes aca
    out = CurriculumStorage()

    # La oferta de majors/minors/titulos de SIDING tiene mucha "basura"
    # Es decir, majors y minors que no son "reales"
    # Para arreglarlo, se compara con la lista scrapeada y contra las mallas que
    # realmente existen
    extract_true_offer(
        "major",
        siding.majors,
        siding,
        chain(
            scraped.majors,
            (major.major or MajorCode("M") for major in bypass.majors),
        ),
        out.offer,
        True,
    )
    extract_true_offer(
        "minor",
        siding.minors,
        siding,
        chain(
            scraped.minors,
            (minor.minor or MinorCode("N") for minor in bypass.minors),
        ),
        out.offer,
        False,
    )
    extract_true_offer(
        "title",
        siding.titles,
        siding,
        chain(
            scraped.titles,
            (title.title or TitleCode("") for title in bypass.titles),
        ),
        out.offer,
        False,
    )

    # Falta extraer los majors y sus minors asociados
    extract_major_minor_associations(siding, out)

    # Traducir los majors desde los datos de SIDING
    for cyear, offer in out.offer.items():
        for major in offer.major.values():
            if major.code not in siding.plans[cyear].plans:
                continue
            spec = CurriculumSpec(
                cyear=cyear,
                major=MajorCode(major.code),
                minor=None,
                title=None,
            )
            translate_major(
                courses,
                out,
                spec,
                siding,
                siding.plans[cyear].plans[major.code],
            )

    # Agregar el plan comun
    translate_common_plan(courses, out, siding)

    # Los minors se traducen desde la informacion scrapeada, y posiblemente ayudados por
    # los datos de SIDING
    for cyear, offer in out.offer.items():
        for minor_meta in offer.minor.values():
            if MinorCode(minor_meta.code) not in scraped.minors:
                continue
            for minor_scrape in scraped.minors[MinorCode(minor_meta.code)]:
                spec = CurriculumSpec(
                    cyear=cyear,
                    major=minor_scrape.assoc_major,
                    minor=minor_scrape.assoc_minor,
                    title=minor_scrape.assoc_title,
                )
                translate_minor(
                    courses,
                    out,
                    spec,
                    minor_meta,
                    siding,
                    siding.plans[cyear].plans.get(minor_meta.code, []),
                    minor_scrape,
                )

    # Los titulos se traducen desde la informacion scrapeada combinada con los datos de
    # SIDING
    for cyear, offer in out.offer.items():
        for title in offer.title.values():
            if TitleCode(title.code) not in scraped.titles:
                continue
            scrape = scraped.titles[TitleCode(title.code)]
            spec = CurriculumSpec(
                cyear=cyear,
                major=scrape.assoc_major,
                minor=scrape.assoc_minor,
                title=scrape.assoc_title,
            )
            translate_title(
                courses,
                out,
                spec,
                title,
                siding,
                siding.plans[cyear].plans.get(title.code, []),
                scrape,
            )

    # Cargar majors minors y titulos desde el bypass
    translate_bypass(courses, siding, bypass, out)

    # Aplicar los ultimos parches faltantes
    patch_globally(courses, out)

    # Tratar las equivalencias homogeneas
    detect_homogeneous(courses, out)

    # Asegurarse que no hayan equivalencias vacias
    for equiv in out.lists.values():
        if not equiv.courses:
            raise Exception(f"list {equiv.code} is empty")

    # Durante la construccion de los curriculums se usa la capacidad -1 como un
    # placeholder, que significa "la capacidad de este nodo es la suma de las
    # capacidades de mis hijos"
    # Por ende, hay que actualizar estas capacidades
    for curr in out.all_plans():
        curr.root.freeze_capacities()

    # TODO: Algunos minors y titulos tienen requerimientos especiales que no son
    #   representables en el formato que provee SIDING, y por ende faltan del
    #   mock (y estan incompletos en el webservice real).
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

    return out


@dataclass
class FilteredCounter:
    not_in_scrape: set[str] = field(default_factory=set)
    no_malla: set[str] = field(default_factory=set)
    not_in_offer: set[str] = field(default_factory=set)


def extract_true_offer(
    kind: str,
    offer: list[Major] | list[Minor] | list[Titulo],
    siding: SidingInfo,
    scraped: Iterable[str],
    out: defaultdict[Cyear, ProgramOffer],
    require_siding: bool,
):
    scraped = set(scraped)
    counter = FilteredCounter()

    # Here, it's clear that filtering a list of a single type will result in a list of a
    # single type
    # However, Python thinks it may result in a list of mixed types, so a type: ignore
    # is needed
    for program in offer:
        for cyear_str in decode_cyears(program.Curriculum):
            cyear = cyear_from_str(cyear_str)
            assert cyear is not None
            result = filter_program(
                cyear,
                program,
                siding,
                scraped,
                counter,
                require_siding,
            )
            if result is not None:
                if isinstance(program, Major):
                    out[cyear].major[result.code] = result
                elif isinstance(program, Minor):
                    out[cyear].minor[result.code] = result
                else:
                    out[cyear].title[result.code] = result

    # Make sure all scraped plans are present in the offer
    available: set[str] = set()
    for program in offer:
        if isinstance(program, Major):
            available.add(program.CodMajor)
        elif isinstance(program, Minor):
            available.add(program.CodMinor)
        else:
            available.add(program.CodTitulo)
    for code in scraped:
        if code not in available:
            counter.not_in_offer.add(code)

    # Print results
    if counter.not_in_scrape:
        log.warning(
            "%s %ss in SIDING offer but not in scraped list: %s",
            len(counter.not_in_scrape),
            kind,
            counter.not_in_scrape,
        )
    if counter.no_malla:
        log.warning(
            "%s %ss are in SIDING offer and scrape"
            ", but have no associated SIDING malla: %s",
            len(counter.no_malla),
            kind,
            counter.no_malla,
        )
    if counter.not_in_offer:
        log.warning(
            "%s %ss in scrape but missing from SIDING offer: %s",
            len(counter.not_in_offer),
            kind,
            counter.not_in_offer,
        )


def filter_program(
    cyear: Cyear,
    program: Major | Minor | Titulo,
    siding: SidingInfo,
    scraped: set[str],
    counter: FilteredCounter,
    require_siding: bool,
) -> ProgramDetails | None:
    """
    Procesar el programa `program`, y convertirlo en un `ProgramDetails`.
    Si determinamos que este programa no esta realmente disponible, retornamos `None`.
    """

    keep_others = False
    if isinstance(program, Major):
        code = program.CodMajor
        version = program.VersionMajor
        program_type = ""
        keep_others = True
    elif isinstance(program, Minor):
        code = program.CodMinor
        version = program.VersionMinor
        program_type = program.TipoMinor
    else:
        code = program.CodTitulo
        version = program.VersionTitulo
        program_type = program.TipoTitulo

    if code not in scraped:
        counter.not_in_scrape.add(code)
        return None

    blocks = filter_relevant_blocks(
        program.Nombre,
        siding.plans[cyear].plans.get(code, []),
        keep_others,
    )
    if not blocks:
        counter.no_malla.add(code)
        if require_siding:
            return None
    siding.plans[cyear].plans[code] = blocks

    return ProgramDetails(
        code=code,
        name=program.Nombre,
        version=version or "",
        program_type=program_type,
    )


def filter_relevant_blocks(
    plan_name: str,
    plan: list[BloqueMalla],
    keep_others: bool,
) -> list[BloqueMalla]:
    for block in plan:
        if _is_block_relevant(plan_name, block):
            break
    else:
        # No hay ningun bloque que calce con el nombre del plan!
        # Es decir, los bloques del plan no tienen nada que ver con lo que se pidio, y
        # por ende el plan es probablemente basura
        return []

    for block in plan:
        if block.CodSigla is None and block.CodLista is None:
            # Que hacer con este bloque??
            return []

    return [
        block for block in plan if _is_block_relevant(plan_name, block) or keep_others
    ]


def _is_block_relevant(plan_name: str, block: BloqueMalla) -> bool:
    return block.Programa == plan_name or block.Programa == "Plan Común"


def extract_major_minor_associations(siding: SidingInfo, out: CurriculumStorage):
    """
    Extraer la asociacion entre majors y minors a partir de la informacion de SIDING.
    """
    for _cyear, offer in out.offer.items():
        for major_code in offer.major:
            offer.major_minor[major_code] = [
                minor.CodMinor
                for minor in siding.major_minor[major_code]
                if minor.CodMinor in offer.minor
            ]


def detect_homogeneous(courses: dict[str, CourseDetails], out: CurriculumStorage):
    """
    Fixes the fillers for homogeneous equivalencies, providing a default choice if all
    options in the equivalence are similar (eg. Optimizacion -> ICS1113).

    There are 3 related concepts at play here: equivalencies, blocks and fillers.
    An equivalency is a list of concrete courses, with some associated metadata (ie.
    name, whether the equivalence is homogeneous or not, etc...).
    A block is a node in a curriculum tree. Most of the time each leaf in the curriculum
    tree has an associated equivalence, but sometimes several blocks share an
    equivalence.
    A filler is the recommended course to fill in a block if the student has not already
    passed a course that satisfies that block. This course may be a concrete course or
    an equivalence, letting the user choose the concrete course from a list.

    Each plan has their own blocks and fillers, but equivalencies are global, have
    unique identifiers and are shared by many plans.
    This function removes the fillers for homogeneous equivalencies, and replaces them
    by fillers that represent concrete courses. In particular, the concrete course that
    represents the homogeneous equivalence.
    """
    for curr in out.all_plans():
        # Fix the fillers
        obsolete_filler_codes: list[str] = []
        new_fillers: dict[str, list[FillerCourse]] = {}
        for filler_code, old_fillers in curr.fillers.items():
            equiv = out.lists.get(filler_code)
            if equiv is not None and (
                (equiv.is_homogeneous and len(equiv.courses) >= 1)
                or len(equiv.courses) == 1
            ):
                # Determine the default course to use
                representative = equiv.courses[0]
                if representative not in courses:
                    raise Exception(
                        f"equivalence {equiv.code}"
                        f" has unknown representative {representative}",
                    )

                # Replace these fillers
                obsolete_filler_codes.append(equiv.code)
                for equiv_filler in old_fillers:
                    assert isinstance(equiv_filler.course, EquivalenceId)
                    new_fillers.setdefault(representative, []).append(
                        FillerCourse(
                            course=ConcreteId(
                                code=representative,
                                equivalence=equiv_filler.course,
                            ),
                            order=equiv_filler.order,
                            cost_offset=equiv_filler.cost_offset,
                        ),
                    )

        # Actually modify the fillers
        for remove_this_code in obsolete_filler_codes:
            del curr.fillers[remove_this_code]
        for add_this_code, add_these_fillers in new_fillers.items():
            curr.fillers.setdefault(add_this_code, []).extend(add_these_fillers)


def patch_globally(courses: dict[str, CourseDetails], out: CurriculumStorage):
    """
    Hay algunos parches que hay que aplicar globalmente sobre todos los curriculums, en
    lugar de uno a uno.
    Estos se aplican aca.
    """

    _mark_homogeneous_equivs(courses, out)
    _mark_unessential_equivs(courses, out)
    _limit_multiplicity(courses, out)
    _force_subcourses(courses, out)


FORCE_HOMOGENEOUS_EQUIVS = (
    {"FIS1523", "ICM1003", "IIQ1003", "IIQ103H"},
    {"FIS1533", "IEE1533"},
    {"ICS1113", "ICS113H"},
)


def _mark_homogeneous_equivs(courses: dict[str, CourseDetails], out: CurriculumStorage):
    max_len = max(len(homogeneous) for homogeneous in FORCE_HOMOGENEOUS_EQUIVS)
    for equiv in out.lists.values():
        if len(equiv.courses) <= max_len and any(
            set(equiv.courses) == homogeneous
            for homogeneous in FORCE_HOMOGENEOUS_EQUIVS
        ):
            equiv.is_homogeneous = True


UNESSENTIAL_EQUIVS = {
    "L1",
    "L2",
    "C10345",
    "C10348",
    "C10349",
    "C10350",
    "C10347",
    "C10346",
    "C10351",
}


def _mark_unessential_equivs(courses: dict[str, CourseDetails], out: CurriculumStorage):
    for list_code, equiv in out.lists.items():
        if any(list_code.endswith(unessential) for unessential in UNESSENTIAL_EQUIVS):
            equiv.is_unessential = True


_MULTIPLICITY_LIMITS = [
    ({"ICS1113", "ICS113H"}, 10),
]


def _limit_multiplicity(courses: dict[str, CourseDetails], out: CurriculumStorage):
    """
    Algunos cursos estan limitados en grupo.
    Por ejemplo, ICS1113 (Optimizacion) y ICS113H (Optimizacion Honors) estan limitados
    a 10 creditos en conjunto.
    Esto significa que si se toman ambos entonces solo 1 va a contar para el curriculum.
    Los cursos pueden estar limitados por-curriculum. Optimizacion en particular, esta
    limitado para todos los curriculums.
    """

    for curr in out.all_plans():
        for group, credit_limit in _MULTIPLICITY_LIMITS:
            mult = Multiplicity(group=group, credits=credit_limit)
            for course in group:
                if course in curr.multiplicity and curr.multiplicity[course] != mult:
                    raise Exception(
                        f"attempt to set multiplicity of {course} to {mult}, "
                        f"but it already has multiplicity {curr.multiplicity[course]}",
                    )
                curr.multiplicity[course] = mult


_FORCE_SUBCOURSES = {
    "ICS1113": "ICS113H",
    "ICS113H": "ICS1113",
}


def _force_subcourses(courses: dict[str, CourseDetails], out: CurriculumStorage):
    """
    Forzamos a que algunos cursos sean "subcursos" de otros.
    En particular, ICS1113 es un subcurso de ICS113H, en el sentido de que cualquier
    bloque que acepte ICS1113 debiera aceptar ICS113H, y cualquier equivalencia que
    contenga ICS1113 debiera contener también a ICS113H.

    Actualmente, ICS113H también es un subcurso de ICS1113, porque Ingenieria acepta que
    los matemáticos que tienen como requisito ICS113H puedan tomar ICS1113 también.
    Si en algún momento cambia esto, hay que cambiar esta función para que ICS113H deje
    de ser un subcurso de ICS1113 (aunque ICS1113 pueda seguir siendo subcurso de
    ICS113H).
    """

    # Add supercourses to equivalencies that only have the subcourse
    for equiv in out.lists.values():
        for sub, super in _FORCE_SUBCOURSES.items():
            if sub in equiv.courses and super not in equiv.courses:
                equiv.courses.append(super)

    # Make all blocks that accept subcourses accept the supercourse
    def add_supercourses(node: Block):
        if isinstance(node, Leaf):
            for sub, super in _FORCE_SUBCOURSES.items():
                if sub in node.codes:
                    node.codes.add(super)
        else:
            for child in node.children:
                add_supercourses(child)

    for curr in out.all_plans():
        add_supercourses(curr.root)


def load_bypass(
    courses: dict[str, CourseDetails],
    scraped: ScrapedInfo,
    siding: SidingInfo,
):
    return BypassInfo.parse_file("../static-curriculum-data/bypass.json")


def translate_bypass(
    courses: dict[str, CourseDetails],
    siding: SidingInfo,
    bypass: BypassInfo,
    out: CurriculumStorage,
):
    """
    Para algunos planes especialmente problematicos, hay una base de datos "hardcodeada"
    a mano, que "bypassea" los procesos de ingesta de datos.
    Este formato se mapea muy directo a la representacion interna, pero es mas facil de
    escribir a mano que el formato interno.
    """
    for cyear, _offer in out.offer.items():
        for bp in bypass.majors:
            spec = CurriculumSpec(
                cyear=cyear,
                major=bp.major,
                minor=bp.minor,
                title=bp.title,
            )
            out.set_major(
                spec,
                bp.plan.translate(courses, siding, out, f"MAJOR-{spec}"),
            )
        for bp in bypass.minors:
            spec = CurriculumSpec(
                cyear=cyear,
                major=bp.major,
                minor=bp.minor,
                title=bp.title,
            )
            out.set_minor(
                spec,
                bp.plan.translate(courses, siding, out, f"MINOR-{spec}"),
            )
        for bp in bypass.titles:
            spec = CurriculumSpec(
                cyear=cyear,
                major=bp.major,
                minor=bp.minor,
                title=bp.title,
            )
            out.set_title(
                spec,
                bp.plan.translate(courses, siding, out, f"TITLE-{spec}"),
            )
