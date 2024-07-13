"""
Transform the Siding format into something usable.
"""

import logging
from dataclasses import dataclass

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
from zeep.exceptions import Fault

from app.plan.course import ConcreteId, PseudoCourse
from app.plan.validation.curriculum.tree import (
    MajorCode,
    MinorCode,
    TitleCode,
    cyear_from_str,
)
from app.sync.siding import client
from app.sync.siding.client import (
    CursoHecho,
    CursoInscrito,
    InfoEstudiante,
    StringArray,
)
from app.user.info import StudentInfo
from app.user.key import Rut


def _decode_curriculum_versions(input: StringArray | None) -> list[str]:
    """
    SIDING returns lists of cyear codes (e.g. ["C2013", "C2020"]) as a convoluted
    `stringArray` type that is currently empty for some reason.
    Transform this type into a more manageable `list[str]`.
    """
    if input is None:
        # Curriculum lists are currently empty for some SIDING reason
        # We are currently patching through the mock
        # TODO: This no longer happens!
        # Although we should probably not depend on SIDING for curriculums, the data is
        # too unreliable
        logging.warning("null curriculum version list")
        return []
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
    majors = {major.CodMajor: major for major in await p_majors}
    for major in majors.values():
        for cyear in _decode_curriculum_versions(major.Curriculum):
            await DbMajor.prisma().create(
                data={
                    "cyear": cyear,
                    "code": major.CodMajor,
                    "name": major.Nombre,
                    "version": major.VersionMajor,
                },
            )

    print("  loading minors")
    minors = {minor.CodMinor: minor for minor in await p_minors}
    for minor in minors.values():
        for cyear in _decode_curriculum_versions(minor.Curriculum):
            await DbMinor.prisma().create(
                data={
                    "cyear": cyear,
                    "code": minor.CodMinor,
                    "name": minor.Nombre,
                    "version": minor.VersionMinor or "",
                    "minor_type": minor.TipoMinor,
                },
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
                },
            )

    print("  loading major-minor associations")
    p_major_minor = [
        (maj, client.get_minors_for_major(maj.CodMajor)) for maj in majors.values()
    ]
    for major, p_assoc_minors in p_major_minor:
        assoc_minors = await p_assoc_minors
        for cyear in _decode_curriculum_versions(major.Curriculum):
            for assoc_minor in assoc_minors:
                minor = minors[assoc_minor.CodMinor]
                if cyear not in _decode_curriculum_versions(minor.Curriculum):
                    continue
                await DbMajorMinor.prisma().create(
                    data={
                        "cyear": cyear,
                        "major": major.CodMajor,
                        "minor": minor.CodMinor,
                    },
                )


class InvalidStudentError(Exception):
    """
    Indicates that the referenced student is not a valid engineering student (as in,
    SIDING does not provide info about them).
    """


@dataclass
class CursosHechos:
    cursos: list[list[PseudoCourse]]
    en_curso: bool
    admision: tuple[int, int] | None


async def _fetch_meta(rut: Rut) -> InfoEstudiante:
    try:
        raw = await client.get_student_info(rut)
        assert raw.Curriculo is not None and raw.Carrera == "INGENIERÍA CIVIL"
    except (AssertionError, Fault) as err:
        if (isinstance(err, Fault) and "no pertenece" in err.message) or isinstance(
            err,
            AssertionError,
        ):
            raise InvalidStudentError("Not a valid engineering student") from err
        raise err
    return raw


async def _fetch_done_courses(rut: Rut) -> CursosHechos:
    raw_prev = await client.get_student_done_courses(rut)
    raw_curr = await client.get_student_current_courses(rut)
    raw: list[CursoHecho | CursoInscrito] = raw_prev + raw_curr

    semesters: list[list[PseudoCourse]] = []
    start_period = None
    last_semester_in_course = False
    if raw:
        # Make sure semester 1 is always odd, adding an empty semester if necessary
        start_year = int(raw[0].Periodo.split("-")[0])
        start_period = (start_year, 1)
        for c in raw:
            sem = _semesters_elapsed(start_period, _decode_period(c.Periodo))
            while len(semesters) <= sem:
                semesters.append([])
            if isinstance(c, CursoHecho):
                if c.Estado == CursoHecho.ESTADO_REPROBADO:
                    # Failed course
                    course = ConcreteId(code="FAILED", equivalence=None, failed=c.Sigla)
                else:
                    # Approved course (or something else?)
                    course = ConcreteId(code=c.Sigla, equivalence=None)
            else:
                # Course in progress
                course = ConcreteId(code=c.Sigla, equivalence=None)
                # Assume that if there is at least 1 course in progress, the entire last
                # semester (and only the last semester) is in progress
                last_semester_in_course = True

            semesters[sem].append(course)

    return CursosHechos(
        cursos=semesters,
        en_curso=last_semester_in_course,
        admision=start_period,
    )


async def fetch_student_info(rut: Rut) -> StudentInfo:
    """
    MUST BE CALLED WITH AUTHORIZATION

    Request all the student information for a given RUT from SIDING.

    Raises `InvalidStudentError` if the RUT does not refer to a valid student.
    """

    raw_meta = await _fetch_meta(rut)
    raw_courses = await _fetch_done_courses(rut)

    assert raw_meta.Curriculo is not None
    return StudentInfo(
        full_name=raw_meta.Nombre,
        cyear=raw_meta.Curriculo,
        is_cyear_supported=cyear_from_str(raw_meta.Curriculo) is not None,
        reported_major=MajorCode(raw_meta.MajorInscrito)
        if raw_meta.MajorInscrito
        else None,
        reported_minor=MinorCode(raw_meta.MinorInscrito)
        if raw_meta.MinorInscrito
        else None,
        reported_title=TitleCode(raw_meta.TituloInscrito)
        if raw_meta.TituloInscrito
        else None,
        passed_courses=raw_courses.cursos,
        next_semester=len(raw_courses.cursos),
        current_semester=len(raw_courses.cursos) - (1 if raw_courses.en_curso else 0),
        admission=raw_courses.admision,
    )
