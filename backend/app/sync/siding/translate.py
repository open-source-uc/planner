"""
Transform the Siding format into something usable.
"""

from typing import Optional

from ...user.info import StudentInfo
from ...plan.courseinfo import CourseInfo, EquivDetails, add_equivalence
from ...plan.course import ConcreteId, EquivalenceId, PseudoCourse
from . import client, curriculum_rules
from .client import (
    BloqueMalla,
    PlanEstudios,
    StringArray,
)
from prisma.models import (
    Major as DbMajor,
    Minor as DbMinor,
    Title as DbTitle,
    MajorMinor as DbMajorMinor,
)
from ...plan.validation.curriculum.tree import (
    Combination,
    Curriculum,
    CurriculumSpec,
    Cyear,
    Block,
    Leaf,
)


def _decode_curriculum_versions(input: Optional[StringArray]) -> list[str]:
    """
    SIDING returns lists of cyear codes (e.g. ["C2013", "C2020"]) as a convoluted
    `stringArray` type that is currently empty for some reason.
    Transform this type into a more manageable `list[str]`.
    """
    if input is None:
        # Why are curriculum versions empty??
        # TODO: Figure out why and remove this code
        return ["C2020"]
    return input.strings.string


def _decode_period(period: str) -> tuple[int, int]:
    """
    Transform a string like "2020-2" to (2020, 2).
    """
    [year, sem] = period.split("-")
    return (int(year), int(sem))


def _semesters_elapsed(start: tuple[int, int], end: tuple[int, int]) -> int:
    """
    Calculate the difference between two periods as a signed number of semesters.
    """
    # Clamp to [1, 2] to handle TAV (semester 3, which should be treated as semester 2)
    s_sem = min(2, max(1, start[1]))
    e_sem = min(2, max(1, end[1]))
    return (end[0] - start[0]) * 2 + (e_sem - s_sem)


async def _fetch_raw_blocks(
    courseinfo: CourseInfo, spec: CurriculumSpec
) -> list[BloqueMalla]:
    """
    NOTE: Blank major/minors raise an error.
    """

    # Fetch raw curriculum blocks for the given cyear-major-minor-title combination
    if spec.major is None or spec.minor is None:
        raise Exception("blank major/minor is not supported")
    raw_blocks = await client.get_curriculum_for_spec(
        PlanEstudios(
            CodCurriculum=str(spec.cyear),
            CodMajor=spec.major,
            CodMinor=spec.minor,
            CodTitulo=spec.title or "",
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
                EquivDetails(
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
                EquivDetails(
                    code=code, name=raw_block.Nombre, is_homogeneous=True, courses=codes
                )
            )

    return raw_blocks


def _patch_capacities(block: Block):
    if isinstance(block, Combination):
        for child in block.children:
            _patch_capacities(child)
        if block.cap == -1:
            c = 0
            for child in block.children:
                c += child.cap
            block.cap = c


async def fetch_curriculum(courseinfo: CourseInfo, spec: CurriculumSpec) -> Curriculum:
    """
    Call into the SIDING webservice and get the curriculum definition for a given spec.

    NOTE: Blank major/minors raise an error.
    """

    print(f"fetching curriculum from siding for spec {spec}")

    raw_blocks = await _fetch_raw_blocks(courseinfo, spec)

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
            if raw_block.CodLista is not None:
                # List equivalence
                code = f"!{raw_block.CodLista}"
            elif raw_block.CodSigla is not None and raw_block.Equivalencias is not None:
                code = f"?{raw_block.CodSigla}"
            else:
                raise Exception("siding api returned invalid curriculum block")
            recommended = EquivalenceId(code=code, credits=raw_block.Creditos)
            # Fetch equivalence data
            info = courseinfo.try_equiv(code)
            assert info is not None
            codes = info.courses
            if info.is_homogeneous and len(codes) >= 1:
                recommended = ConcreteId(code=codes[0], equivalence=recommended)
        creds = raw_block.Creditos
        if creds == 0:
            # 0-credit courses get a single ghost credit
            creds = 1
        codes_dict = {}
        codes_dict[code] = None
        for code in codes:
            codes_dict[code] = 1
        recommended_priority = raw_block.SemestreBloque * 10 + raw_block.OrdenSemestre
        superblock = superblocks.setdefault(raw_block.BloqueAcademico, [])
        superblock.append(
            Leaf(
                name=raw_block.Nombre,
                cap=creds,
                codes=codes_dict,
                fill_with=[
                    (
                        recommended_priority,
                        recommended,
                    )
                ],
            )
        )

    # Transform into a somewhat valid curriculum
    root = Combination(cap=-1, children=[])
    for superblock_name, leaves in superblocks.items():
        root.children.append(Combination(name=superblock_name, cap=-1, children=leaves))
    curriculum = Curriculum(root=root)

    # Apply custom cyear-dependent transformations
    curriculum = await curriculum_rules.apply_curriculum_rules(
        courseinfo, spec, curriculum
    )

    # Patch any `-1` capacities to be the sum of child capacities
    _patch_capacities(curriculum.root)

    return curriculum


async def load_siding_offer_to_database():
    """
    Call into the SIDING webservice and fetch majors, minors and titles.
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
        for cyear in _decode_curriculum_versions(major.Curriculum):
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
        for cyear in _decode_curriculum_versions(minor.Curriculum):
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
        for cyear in _decode_curriculum_versions(title.Curriculum):
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
        for cyear in _decode_curriculum_versions(major.Curriculum):
            for minor in assoc_minors:
                if cyear not in _decode_curriculum_versions(minor.Curriculum):
                    continue
                await DbMajorMinor.prisma().create(
                    data={
                        "cyear": cyear,
                        "major": major.CodMajor,
                        "minor": minor.CodMinor,
                    }
                )


async def fetch_student_info(rut: str) -> StudentInfo:
    """
    MUST BE CALLED WITH AUTHORIZATION

    Request the basic student information for a given RUT from SIDING.
    """
    raw = await client.get_student_info(rut)
    return StudentInfo(
        full_name=raw.Nombre,
        cyear=raw.Curriculo,
        is_cyear_supported=Cyear.from_str(raw.Curriculo) is not None,
        admission=_decode_period(raw.PeriodoAdmision),
        reported_major=raw.MajorInscrito,
        reported_minor=raw.MinorInscrito,
        reported_title=raw.TituloInscrito,
    )


async def fetch_student_previous_courses(
    rut: str, info: StudentInfo
) -> list[list[PseudoCourse]]:
    """
    MUST BE CALLED WITH AUTHORIZATION

    Make a request to SIDING to find out the courses that the given student has passed.
    """

    raw = await client.get_student_done_courses(rut)
    semesters: list[list[PseudoCourse]] = []
    # Make sure semester 1 is always odd, adding an empty semester if necessary
    start_period = (info.admission[0], 1)
    for c in raw:
        sem = _semesters_elapsed(start_period, _decode_period(c.Periodo))
        while len(semesters) <= sem:
            semesters.append([])
        semesters[sem].append(ConcreteId(code=c.Sigla))
    return semesters
