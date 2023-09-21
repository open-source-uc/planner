"""
Collates information from various sources to build a complete curriculum plan
specification.
"""

import logging

from pydantic import BaseModel

from app.plan.course import ConcreteId, EquivalenceId
from app.plan.courseinfo import CourseInfo, add_equivalence, course_info
from app.plan.validation.curriculum.tree import (
    CurriculumSpec,
    Cyear,
    FillerCourse,
    Multiplicity,
)
from app.sync.curriculums.major import translate_common_plan, translate_major
from app.sync.curriculums.minor import translate_minor
from app.sync.curriculums.scrape.common import ScrapedProgram
from app.sync.curriculums.scrape.minor import scrape_minors
from app.sync.curriculums.scrape.title import scrape_titles
from app.sync.curriculums.siding import SidingInfo, fetch_siding
from app.sync.curriculums.storage import CurriculumStorage
from app.sync.curriculums.title import translate_title
from app.sync.siding.client import (
    BloqueMalla,
    Major,
    Minor,
    Titulo,
    decode_cyears,
)

log = logging.getLogger("plan-collator")


class ScrapedInfo(BaseModel):
    minors: dict[str, ScrapedProgram]
    titles: dict[str, ScrapedProgram]


async def collate_plans() -> CurriculumStorage:
    # Fetch course database
    courseinfo = await course_info()

    # Scrape information from PDFs
    scraped = ScrapedInfo(
        minors=scrape_minors(courseinfo),
        titles=scrape_titles(courseinfo),
    )

    # Fetch information from SIDING
    siding = await fetch_siding(courseinfo)

    # Algunos majors/minors/titulos pueden no ser relevantes
    # Por ejemplo, algunos majors podrian no tener informacion de plan disponible en
    # SIDING, o algunos minors o titulos podrian no estar en el scrape
    filter_relevant_programs(siding, scraped)

    # Colocar los curriculums resultantes aca
    out = CurriculumStorage()

    # Traducir los majors desde los datos de SIDING
    for major in siding.majors:
        for cyear_str in decode_cyears(major.Curriculum):
            cyear = Cyear.from_str(cyear_str)
            assert cyear is not None
            spec = CurriculumSpec(
                cyear=cyear,
                major=major.CodMajor,
                minor=None,
                title=None,
            )
            translate_major(
                courseinfo,
                out,
                spec,
                siding,
                siding.plans[cyear].plans[major.CodMajor],
            )

    # Agregar el plan comun
    translate_common_plan(courseinfo, out, siding)

    # Los minors se traducen desde la informacion scrapeada, y posiblemente ayudados por
    # los datos de SIDING
    for minor in siding.minors:
        for cyear_str in decode_cyears(minor.Curriculum):
            cyear = Cyear.from_str(cyear_str)
            assert cyear is not None
            spec = CurriculumSpec(
                cyear=cyear,
                major=None,
                minor=minor.CodMinor,
                title=None,
            )
            translate_minor(
                courseinfo,
                out,
                spec,
                minor,
                siding.plans[cyear].plans[minor.CodMinor],
                scraped.minors[minor.CodMinor],
            )

    # Los titulos se traducen desde la informacion scrapeada combinada con los datos de
    # SIDING
    for title in siding.titles:
        for cyear_str in decode_cyears(title.Curriculum):
            cyear = Cyear.from_str(cyear_str)
            assert cyear is not None
            spec = CurriculumSpec(
                cyear=cyear,
                major=None,
                minor=None,
                title=title.CodTitulo,
            )
            translate_title(
                courseinfo,
                out,
                spec,
                title,
                siding.plans[cyear].plans[title.CodTitulo],
                scraped.titles[title.CodTitulo],
            )

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
    # out.lists.clear()

    return out


def filter_relevant_programs(siding: SidingInfo, scraped: ScrapedInfo):
    # Filtrar los majors que realmente estan disponibles
    # Los majors no disponibles tienen informacion basura, que corresponde a otros
    # programas
    # Hay que filtrar esta basura
    new_majors: list[Major] = []
    for major in siding.majors:
        for cyear_str in decode_cyears(major.Curriculum):
            cyear = Cyear.from_str(cyear_str)
            assert cyear is not None
            blocks = filter_relevant_blocks(
                major.Nombre,
                siding.plans[cyear].plans[major.CodMajor],
                True,
            )
            if blocks is not None:
                new_majors.append(major)
                siding.plans[cyear].plans[major.CodMajor] = blocks
            else:
                log.warning(
                    "el major %s no esta disponible en la base de datos de SIDING",
                    major.CodMajor,
                )
    siding.majors = new_majors

    # Filtrar los minors por los que estan realmente disponibles en la informacion
    # scrapeada
    new_minors: list[Minor] = []
    for minor in siding.minors:
        if minor.CodMinor not in scraped.minors:
            log.warning(
                "el minor %s esta en la oferta de SIDING pero no esta"
                " en el scrape de los planes de estudio, skipeandolo",
            )
            continue
        new_minors.append(minor)

        for cyear_str in decode_cyears(minor.Curriculum):
            cyear = Cyear.from_str(cyear_str)
            assert cyear is not None
            blocks = filter_relevant_blocks(
                minor.Nombre,
                siding.plans[cyear].plans[minor.CodMinor],
                False,
            )
            if blocks is None:
                log.warning(
                    "el plan para el minor %s no esta disponible en SIDING",
                    minor.CodMinor,
                )
                blocks = []
            siding.plans[cyear].plans[minor.CodMinor] = blocks
    siding.minors = new_minors

    # Filtrar los titulos por los que estan realmente disponibles en la informacion
    # scrapeada
    new_titles: list[Titulo] = []
    for title in siding.titles:
        if title.CodTitulo not in scraped.titles:
            log.warning(
                "el titulo %s esta en la oferta de SIDING pero no esta"
                " en el scrape de los planes de estudio, skipeandolo",
            )
            continue
        new_titles.append(title)

        for cyear_str in decode_cyears(title.Curriculum):
            cyear = Cyear.from_str(cyear_str)
            assert cyear is not None
            blocks = filter_relevant_blocks(
                title.Nombre,
                siding.plans[cyear].plans[title.CodTitulo],
                False,
            )
            if blocks is None:
                log.warning(
                    "el plan para el titulo %s no esta disponible en SIDING",
                    title.CodTitulo,
                )
                blocks = []
            siding.plans[cyear].plans[title.CodTitulo] = blocks
    siding.titles = new_titles


def filter_relevant_blocks(
    plan_name: str,
    plan: list[BloqueMalla],
    keep_others: bool,
) -> list[BloqueMalla] | None:
    for block in plan:
        if _is_block_relevant(plan_name, block):
            break
    else:
        # No hay ningun bloque que calce con el nombre del plan!
        # Es decir, los bloques del plan no tienen nada que ver con lo que se pidio, y
        # por ende el plan es probablemente basura
        return None

    return [
        block for block in plan if _is_block_relevant(plan_name, block) or keep_others
    ]


def _is_block_relevant(plan_name: str, block: BloqueMalla) -> bool:
    return block.Programa == plan_name or block.Programa == "Plan Común"


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
