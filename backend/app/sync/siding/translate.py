"""
Transform the Siding format into something usable.
"""

from ...plan.courseinfo import CourseInfo, add_equivalence
from ...plan.plan import ConcreteId, EquivalenceId, PseudoCourse
from ...plan.validation.curriculum.solve import DEBUG_SOLVE
from . import client
from .client import (
    BloqueMalla,
    PlanEstudios,
)
from prisma.models import (
    Major as DbMajor,
    Minor as DbMinor,
    Title as DbTitle,
    MajorMinor as DbMajorMinor,
    Equivalence as DbEquivalence,
)
from ...plan.validation.curriculum.tree import (
    Block,
    Curriculum,
    CourseList,
    CurriculumSpec,
    Node,
)


async def _fetch_raw_blocks(
    courseinfo: CourseInfo, spec: CurriculumSpec
) -> list[BloqueMalla]:
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

    # Fetch data for unseen equivalences
    for raw_block in raw_blocks:
        if raw_block.CodLista is not None:
            code = f"!{raw_block.CodLista}"
            if courseinfo.try_equiv(code) is not None:
                continue
            raw_courses = await client.get_predefined_list(raw_block.CodLista)
            codes = list(map(lambda c: c.Sigla, raw_courses))
            await add_equivalence(
                DbEquivalence(
                    code=code,
                    name=raw_block.Nombre,
                    # TODO: Do some deeper analysis to determine if an equivalency is
                    # homogeneous
                    is_homogeneous=len(codes) < 5,
                    courses=codes,
                )
            )
        elif raw_block.CodSigla is not None and raw_block.Equivalencias is not None:
            code = f"?{raw_block.CodSigla}"
            if courseinfo.try_equiv(code) is not None:
                continue
            codes = [raw_block.CodSigla]
            for equiv in raw_block.Equivalencias.Cursos:
                codes.append(equiv.Sigla)
            await add_equivalence(
                DbEquivalence(
                    code=code, name=raw_block.Nombre, is_homogeneous=True, courses=codes
                )
            )

    return raw_blocks


async def fetch_curriculum_from_siding(
    courseinfo: CourseInfo, spec: CurriculumSpec
) -> Curriculum:
    print(f"fetching curriculum from siding for spec {spec}")

    raw_blocks = await _fetch_raw_blocks(courseinfo, spec)

    # Transform into standard blocks
    blocks: list[Node] = []
    for i, raw_block in enumerate(raw_blocks):
        if raw_block.CodLista is not None:
            # Predefined list
            equiv_code = f"!{raw_block.CodLista}"
            codes = courseinfo.equiv(equiv_code).courses
        elif raw_block.CodSigla is not None:
            # Course codes
            if raw_block.Equivalencias is None:
                codes = [raw_block.CodSigla]
                equiv_code = None
            else:
                equiv_code = f"?{raw_block.CodSigla}"
                codes = courseinfo.equiv(equiv_code).courses
        else:
            raise Exception("siding api returned invalid curriculum block")
        creds = raw_block.Creditos
        if creds is None:
            creds = 0
        course = CourseList(
            name=raw_block.Nombre,
            cap=creds,
            codes=codes,
            priority=i,
            superblock=raw_block.BloqueAcademico,
            equivalence_code=equiv_code,
        )
        blocks.append(course)

    # Apply OFG transformation (merge all OFGs into a single 50-credit block, and only
    # allow up to 10 credits of 5-credit sports courses)
    if spec.cyear == "C2020":
        ofg_course = None
        for i in reversed(range(len(blocks))):
            block = blocks[i]
            if isinstance(block, CourseList) and block.equivalence_code == "!L1":
                if ofg_course is None:
                    ofg_course = block
                else:
                    ofg_course.cap += block.cap
                blocks.pop(i)
        if ofg_course is not None:
            non_5_credits = ofg_course.copy(
                update={
                    "codes": list(
                        filter(
                            lambda c: courseinfo.course(c).credits != 5,
                            ofg_course.codes,
                        )
                    ),
                }
            )
            yes_5_credits = ofg_course.copy(
                update={
                    "codes": list(
                        filter(
                            lambda c: courseinfo.course(c).credits == 5,
                            ofg_course.codes,
                        )
                    ),
                    "cap": 10,
                }
            )
            blocks.append(
                Block(
                    superblock=ofg_course.superblock,
                    name=ofg_course.name,
                    cap=ofg_course.cap,
                    children=[non_5_credits, yes_5_credits],
                )
            )
    else:
        raise Exception(f"unsupported curriculum year '{spec.cyear}'")

    # TODO: Apply title transformation (130 credits must be exclusive to the title, the
    # rest can be shared)

    # Sort by number of satisfying courses
    # TODO: Figure out proper validation order, or if flow has to be used.
    blocks.sort(key=lambda b: len(b.codes) if isinstance(b, CourseList) else 1e6)

    return Curriculum(nodes=blocks)


async def fetch_recommended_courses_from_siding(
    courseinfo: CourseInfo,
    spec: CurriculumSpec,
) -> list[list[PseudoCourse]]:
    print(f"fetching recommended courses from siding for spec {spec}")

    # Fetch raw curriculum blocks for the given cyear-major-minor-title combination
    raw_blocks = await _fetch_raw_blocks(courseinfo, spec)

    # Courses belonging to these superblocks will be skipped
    skip_superblocks = [
        "Requisitos adicionales para obtener el grado de "
        "Licenciado en Ciencias de la Ingeniería",
        "Requisitos adicionales para obtener el Título Profesional",
    ]

    # Transform into a list of lists of pseudocourse ids
    semesters: list[list[PseudoCourse]] = []
    for raw_block in raw_blocks:
        if raw_block.BloqueAcademico in skip_superblocks:
            continue
        if raw_block.CodLista is not None:
            representative_course = EquivalenceId(
                code=f"!{raw_block.CodLista}", credits=raw_block.Creditos
            )
        elif raw_block.CodSigla is not None:
            if raw_block.Equivalencias is not None and raw_block.Equivalencias.Cursos:
                representative_course = ConcreteId(
                    code=raw_block.CodSigla,
                    equivalence=EquivalenceId(
                        code=f"?{raw_block.CodSigla}", credits=raw_block.Creditos
                    ),
                )
            else:
                representative_course = ConcreteId(code=raw_block.CodSigla)
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
