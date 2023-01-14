"""
Transform the Siding format into something usable.
"""

from ...plan.validation.curriculum.solve import DEBUG_SOLVE
from ...plan.validation.courses.logic import Expr, Operator
from ...plan.courseinfo import course_info
from . import client
from .client import (
    PlanEstudios,
    Curso as CursoSiding,
)
from prisma.models import (
    Major as DbMajor,
    Minor as DbMinor,
    Title as DbTitle,
    MajorMinor as DbMajorMinor,
)
from ...plan.validation.curriculum.tree import (
    Curriculum,
    CourseList,
    CurriculumSpec,
    Node,
)
import random

_predefined_list_cache: dict[str, list[CursoSiding]] = {}


async def predefined_list(list_code: str) -> list[CursoSiding]:
    if list_code in _predefined_list_cache:
        return _predefined_list_cache[list_code]
    rawlist = await client.get_predefined_list(list_code)
    _predefined_list_cache[list_code] = rawlist
    return rawlist


async def fetch_curriculum_from_siding(spec: CurriculumSpec) -> Curriculum:
    # Fetch raw curriculum blocks for the given cyear-major-minor-title combination
    if spec.major is None or spec.minor is None or spec.title is None:
        raise Exception("blank major/minor/titles are not supported yet")
    raw_blocks = await client.get_curriculum_for_spec(
        PlanEstudios(
            CodCurriculum=spec.cyear,
            CodMajor=spec.major,
            CodMinor=spec.minor,
            CodTitulo=spec.title,
        )
    )

    # Transform into standard blocks
    blocks: list[Node] = []
    for i, raw_block in enumerate(raw_blocks):
        if raw_block.CodLista is not None:
            # Predefined list
            raw_courses = await predefined_list(raw_block.CodLista)
            codes = list(map(lambda c: c.Sigla, raw_courses))
        elif raw_block.CodSigla is not None:
            # Course codes
            codes = [raw_block.CodSigla]
            if raw_block.Equivalencias is not None:
                for equiv in raw_block.Equivalencias.Cursos:
                    codes.append(equiv.Sigla)
        else:
            raise Exception("siding api returned invalid curriculum block")
        course = CourseList(
            name=raw_block.Nombre,
            cap=raw_block.Creditos,
            codes=codes,
            priority=i,
            superblock=raw_block.BloqueAcademico,
        )
        blocks.append(course)

    # TODO: Apply OFG transformation (merge all OFGs into a single 50-credit block, and
    # only allow up to 10 credits of 5-credit sports courses)

    # TODO: Apply title transformation (130 credits must be exclusive to the title, the
    # rest can be shared)

    # Sort by number of satisfying courses
    # TODO: Figure out proper validation order, or if flow has to be used.
    blocks.sort(key=lambda b: len(b.codes) if isinstance(b, CourseList) else 1e6)

    return Curriculum(nodes=blocks)


async def _debug_pick_good_course(
    taken: list[list[str]], courselist: list[CursoSiding]
) -> CursoSiding:
    def count_nodes(expr: Expr) -> int:
        cnt = 1
        if isinstance(expr, Operator):
            for child in expr.children:
                cnt += count_nodes(child)
        return cnt

    courseinfo = await course_info()
    best = None
    best_cnt = 99999999
    for _ in range(100):
        c = random.choice(courselist)
        if best is None:
            best = c
        if c.Sigla not in courseinfo:
            continue
        if courseinfo[c.Sigla].credits < 10:
            continue
        skip = False
        for semester in taken:
            if c.Sigla in semester:
                skip = True
        if skip:
            continue
        cnt = count_nodes(courseinfo[c.Sigla].deps)
        if cnt < best_cnt:
            best = c
            best_cnt = cnt
    assert best is not None
    return best


async def fetch_recommended_courses_from_siding(
    spec: CurriculumSpec,
) -> list[list[str]]:
    # Fetch raw curriculum blocks for the given cyear-major-minor-title combination
    if spec.major is None or spec.minor is None or spec.title is None:
        raise Exception("blank major/minor/titles are not supported yet")
    raw_blocks = await client.get_curriculum_for_spec(
        PlanEstudios(
            CodCurriculum=spec.cyear,
            CodMajor=spec.major,
            CodMinor=spec.minor,
            CodTitulo=spec.title,
        )
    )

    # Courses belonging to these superblocks will be skipped
    skip_superblocks = [
        "Requisitos adicionales para obtener el grado de "
        "Licenciado en Ciencias de la Ingeniería",
        "Requisitos adicionales para obtener el Título Profesional",
    ]

    # Transform into a list of lists of course codes
    semesters: list[list[str]] = []
    for raw_block in raw_blocks:
        if raw_block.BloqueAcademico in skip_superblocks:
            continue
        if raw_block.CodLista is not None:
            # TODO: Replace by an ambiguous course
            representative_course = (
                await _debug_pick_good_course(
                    semesters, await predefined_list(raw_block.CodLista)
                )
            ).Sigla
        elif raw_block.CodSigla is not None:
            # TODO: Consider using an ambiguous course for some equivalencies
            representative_course = raw_block.CodSigla
        else:
            raise Exception("invalid siding curriculum block")
        semester_number = raw_block.SemestreBloque
        semester_idx = semester_number - 1  # We use 0-based indices here
        while len(semesters) <= semester_idx:
            semesters.append([])
        semesters[semester_idx].append(representative_course)
        if DEBUG_SOLVE:
            print(
                f"selected course {representative_course} for block {raw_block.Nombre}"
            )

    return semesters


async def load_offer_to_database():
    """
    Fetch majors, minors and titles.
    """

    print("loading major/minor/title offer to database...")

    print("  clearing previous data")
    await DbMajor.prisma().delete_many()
    await DbMinor.prisma().delete_many()
    await DbTitle.prisma().delete_many()
    await DbMajorMinor.prisma().delete_many()

    print("  loading majors")
    majors = await client.get_majors()
    for major in majors:
        for cyear in major.Curriculum.strings.string:
            await DbMajor.prisma().create(
                data={
                    "cyear": cyear,
                    "code": major.CodMajor,
                    "name": major.Nombre,
                    "version": major.VersionMajor,
                }
            )

    print("  loading minors")
    minors = await client.get_minors()
    for minor in minors:
        for cyear in minor.Curriculum.strings.string:
            await DbMinor.prisma().create(
                data={
                    "cyear": cyear,
                    "code": minor.CodMinor,
                    "name": minor.Nombre,
                    "version": minor.VersionMinor or "",
                    "minor_type": minor.TipoMinor,
                }
            )

    print("  loading titles")
    titles = await client.get_titles()
    for title in titles:
        for cyear in title.Curriculum.strings.string:
            await DbTitle.prisma().create(
                data={
                    "cyear": cyear,
                    "code": title.CodTitulo,
                    "name": title.Nombre,
                    "version": title.VersionTitulo or "",
                    "title_type": title.TipoTitulo,
                }
            )

    print("  loading major-minor associations")
    for major in majors:
        assoc_minors = await client.get_minors_for_major(major.CodMajor)
        for cyear in major.Curriculum.strings.string:
            for minor in assoc_minors:
                if cyear not in minor.Curriculum.strings.string:
                    continue
                await DbMajorMinor.prisma().create(
                    data={
                        "cyear": cyear,
                        "major": major.CodMajor,
                        "minor": minor.CodMinor,
                    }
                )
