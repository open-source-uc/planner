"""
Transform the Siding format into something usable.
"""

from typing import Optional

from prisma.models import (
    Major as DbMajor,
)
from prisma.models import (
    MajorMinor as DbMajorMinor,
)
from prisma.models import (
    Minor as DbMinor,
)
from prisma.models import (
    Title as DbTitle,
)

from ...plan.course import ConcreteId, EquivalenceId, PseudoCourse
from ...plan.courseinfo import CourseInfo, EquivDetails, add_equivalence
from ...plan.validation.curriculum.tree import (
    Block,
    Combination,
    CourseRecommendation,
    Curriculum,
    CurriculumSpec,
    Cyear,
    Leaf,
)
from ...user.info import StudentInfo
from . import client, siding_rules
from .client import (
    BloqueMalla,
    PlanEstudios,
    StringArray,
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

    # Use a dummy major and minor if they are not specified
    # Later, remove this information
    major = "M245" if spec.major is None else spec.major
    minor = "N344" if spec.minor is None else spec.minor

    # Fetch raw curriculum blocks for the given cyear-major-minor-title combination
    raw_blocks = await client.get_curriculum_for_spec(
        PlanEstudios(
            CodCurriculum=str(spec.cyear),
            CodMajor=major,
            CodMinor=minor,
            CodTitulo=spec.title or "",
        )
    )

    # Remove data if a dummy major/minor was used
    if spec.major is None:
        raw_blocks = list(
            filter(
                lambda raw_block: not raw_block.BloqueAcademico.startswith("Major"),
                raw_blocks,
            )
        )
    if spec.minor is None:
        raw_blocks = list(
            filter(
                lambda raw_block: not raw_block.BloqueAcademico.startswith("Minor"),
                raw_blocks,
            )
        )

    # Fetch data for unseen equivalences
    for raw_block in raw_blocks:
        equiv = None
        if raw_block.CodLista is not None:
            code = f"!{raw_block.CodLista}"
            if courseinfo.try_equiv(code) is not None:
                continue
            raw_courses = await client.get_predefined_list(raw_block.CodLista)
            codes: list[str] = []
            for c in raw_courses:
                if courseinfo.try_course(c.Sigla) is None:
                    print(
                        f"unknown course {c.Sigla} in SIDING list"
                        + f" {raw_block.CodLista} ({raw_block.Nombre})"
                    )
                else:
                    codes.append(c.Sigla)
            equiv = EquivDetails(
                code=code,
                name=raw_block.Nombre,
                is_homogeneous=False,
                is_unessential=False,
                courses=codes,
            )
        elif raw_block.CodSigla is not None and raw_block.Equivalencias is not None:
            code = f"?{raw_block.CodSigla}"
            if courseinfo.try_equiv(code) is not None:
                continue
            codes = [raw_block.CodSigla]
            for equiv in raw_block.Equivalencias.Cursos:
                codes.append(equiv.Sigla)
            equiv = EquivDetails(
                code=code,
                name=raw_block.Nombre,
                is_homogeneous=True,
                is_unessential=True,
                courses=codes,
            )
        if equiv is not None:
            equiv = await siding_rules.apply_equivalence_rules(courseinfo, spec, equiv)
            await add_equivalence(equiv)

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
        recommended_order = raw_block.SemestreBloque * 10 + raw_block.OrdenSemestre
        superblock = superblocks.setdefault(raw_block.BloqueAcademico, [])
        superblock.append(
            Leaf(
                name=raw_block.Nombre,
                cap=creds,
                codes=codes_dict,
                fill_with=[
                    CourseRecommendation(course=recommended, order=recommended_order)
                ],
            )
        )

    # Transform into a somewhat valid curriculum
    root = Combination(cap=-1, children=[])
    for superblock_name, leaves in superblocks.items():
        root.children.append(Combination(name=superblock_name, cap=-1, children=leaves))
    curriculum = Curriculum(root=root)

    # Apply custom cyear-dependent transformations
    curriculum = await siding_rules.apply_curriculum_rules(courseinfo, spec, curriculum)

    # Patch any `-1` capacities to be the sum of child capacities
    _patch_capacities(curriculum.root)

    return curriculum


async def load_siding_offer_to_database():
    """
    Call into the SIDING webservice and fetch majors, minors and titles.
    """

    print("loading major/minor/title offer to database...")

    print("  loading majors")
    p_majors, p_minors, p_titles = (
        client.get_majors(),
        client.get_minors(),
        client.get_titles(),
    )
    majors = await p_majors
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
    for minor in await p_minors:
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
    for title in await p_titles:
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
    p_major_minor = list(
        map(lambda maj: (maj, client.get_minors_for_major(maj.CodMajor)), majors)
    )
    for major, p_assoc_minors in p_major_minor:
        assoc_minors = await p_assoc_minors
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
