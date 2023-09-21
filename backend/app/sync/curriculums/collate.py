"""
Collates information from various sources to build a complete curriculum plan
specification.
"""

import logging
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

from pydantic import BaseModel

from app.plan.course import ConcreteId, EquivalenceId
from app.plan.courseinfo import CourseInfo, add_equivalence, course_info
from app.plan.validation.curriculum.tree import (
    CurriculumSpec,
    Cyear,
    FillerCourse,
    MajorCode,
    MinorCode,
    Multiplicity,
    TitleCode,
    cyear_from_str,
)
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


class ScrapedInfo(BaseModel):
    majors: set[str]
    minors: dict[str, ScrapedProgram]
    titles: dict[str, ScrapedProgram]


async def collate_plans() -> CurriculumStorage:
    # Fetch course database
    courseinfo = await course_info()

    # Scrape information from PDFs
    scraped = ScrapedInfo(
        majors=scrape_majors(),
        minors=scrape_minors(courseinfo),
        titles=scrape_titles(courseinfo),
    )

    # Fetch information from SIDING
    siding = await fetch_siding(courseinfo)

    # Colocar los curriculums resultantes aca
    out = CurriculumStorage()

    # La oferta de majors/minors/titulos de SIDING tiene mucha "basura"
    # Es decir, majors y minors que no son "reales"
    # Para arreglarlo, se compara con la lista scrapeada y contra las mallas que
    # realmente existen
    extract_true_offer("major", siding.majors, siding, scraped.majors, out.offer, True)
    extract_true_offer("minor", siding.minors, siding, scraped.minors, out.offer, False)
    extract_true_offer("title", siding.titles, siding, scraped.titles, out.offer, False)

    # Falta extraer los majors y sus minors asociados
    extract_major_minor_associations(siding, out)

    # Algunos titulos se agregan manualmente
    add_manual_title_offer(siding, out)

    # Traducir los majors desde los datos de SIDING
    for cyear, offer in out.offer.items():
        for major in offer.major.values():
            spec = CurriculumSpec(
                cyear=cyear,
                major=MajorCode(major.code),
                minor=None,
                title=None,
            )
            translate_major(
                courseinfo,
                out,
                spec,
                siding,
                siding.plans[cyear].plans.get(major.code, []),
            )

    # Agregar el plan comun
    translate_common_plan(courseinfo, out, siding)

    # Los minors se traducen desde la informacion scrapeada, y posiblemente ayudados por
    # los datos de SIDING
    for cyear, offer in out.offer.items():
        for minor in offer.minor.values():
            spec = CurriculumSpec(
                cyear=cyear,
                major=None,
                minor=MinorCode(minor.code),
                title=None,
            )
            translate_minor(
                courseinfo,
                out,
                spec,
                minor,
                siding.plans[cyear].plans.get(minor.code, []),
                scraped.minors[minor.code],
            )

    # Los titulos se traducen desde la informacion scrapeada combinada con los datos de
    # SIDING
    for cyear, offer in out.offer.items():
        for title in offer.title.values():
            spec = CurriculumSpec(
                cyear=cyear,
                major=None,
                minor=None,
                title=TitleCode(title.code),
            )
            translate_title(
                courseinfo,
                out,
                spec,
                title,
                siding.plans[cyear].plans.get(title.code, []),
                scraped.titles[title.code],
            )

    # Aplicar los ultimos parches faltantes
    patch_globally(courseinfo, out)

    # Tratar las equivalencias homogeneas
    detect_homogeneous(courseinfo, out)

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

    # Agregar las listas a la base de datos global
    for equiv in out.lists.values():
        await add_equivalence(equiv)

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
                set(scraped),
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
        siding.plans[cyear].plans[code],
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


def detect_homogeneous(courseinfo: CourseInfo, out: CurriculumStorage):
    warned_about: set[tuple[str, str]] = set()

    for equiv in out.lists.values():
        if equiv.is_homogeneous and len(equiv.courses) >= 1:
            concrete = courseinfo.try_course(equiv.courses[0])
            if concrete is None:
                raise Exception(
                    f"equivalence {equiv.code}"
                    f" has unknown representative {equiv.courses[0]}",
                )
            recommend = ConcreteId(
                code=concrete.code,
                equivalence=EquivalenceId(code=equiv.code, credits=concrete.credits),
            )

            # Make this equivalence homogeneous across all plans
            for curr in out.all_plans():
                # Fix up multiplicity
                # This means that a common credit pool is shared among all courses in
                # the equivalence
                credits = curr.multiplicity_of(courseinfo, concrete.code).credits
                courses = set(equiv.courses)
                courses.add(equiv.code)
                for equivalent in equiv.courses:
                    if equivalent not in curr.multiplicity:
                        curr.multiplicity[equivalent] = curr.multiplicity_of(
                            courseinfo,
                            equivalent,
                        )
                    equivalent_mult = curr.multiplicity[equivalent]
                    if equivalent_mult.credits != credits:
                        if (equivalent, equiv.code) not in warned_about:
                            log.warning(
                                f"course {equivalent}"
                                f" (multiplicity of {equivalent_mult.credits})"
                                f" is part of homogeneous equivalence {equiv.code}"
                                f" (multiplicity of {credits} credits)"
                                f", assuming {credits} credits",
                            )
                            warned_about.add((equivalent, equiv.code))
                        equivalent_mult.credits = credits
                    equivalent_mult.group.update(courses)
                curr.multiplicity[equiv.code] = Multiplicity(
                    group=courses,
                    credits=credits,
                )

                # Fix up the fillers
                # Make it so that the filler is a concrete course linked to the
                # equivalence
                if equiv.code in curr.fillers:
                    for old_filler in curr.fillers[equiv.code]:
                        new_filler = FillerCourse(
                            course=recommend,
                            order=old_filler.order,
                            cost_offset=old_filler.cost_offset,
                        )
                        curr.fillers.setdefault(concrete.code, []).append(new_filler)
                    del curr.fillers[equiv.code]


def patch_globally(courseinfo: CourseInfo, out: CurriculumStorage):
    """
    Hay algunos parches que hay que aplicar globalmente sobre todos los curriculums, en
    lugar de uno a uno.
    Estos se aplican aca.
    """

    _mark_homogeneous_equivs(courseinfo, out)
    _mark_unessential_equivs(courseinfo, out)


FORCE_HOMOGENEOUS_EQUIVS = (
    {"FIS1523", "ICM1003", "IIQ1003", "IIQ103H"},
    {"FIS1533", "IEE1533"},
    {"ICS1113", "ICS113H"},
)


def _mark_homogeneous_equivs(courseinfo: CourseInfo, out: CurriculumStorage):
    max_len = max(len(homogeneous) for homogeneous in FORCE_HOMOGENEOUS_EQUIVS)
    for equiv in out.lists.values():
        if len(equiv.courses) <= max_len and any(
            set(equiv.courses) == homogeneous
            for homogeneous in FORCE_HOMOGENEOUS_EQUIVS
        ):
            equiv.is_homogeneous = True


UNESSENTIAL_EQUIVS = {
    "!L1",
    "!L2",
    "!C10345",
    "!C10348",
    "!C10349",
    "!C10350",
    "!C10347",
    "!C10346",
    "!C10351",
}


def _mark_unessential_equivs(courseinfo: CourseInfo, out: CurriculumStorage):
    for unessential_code in UNESSENTIAL_EQUIVS:
        out.lists[unessential_code].is_unessential = True
