"""
Update local database with an official but ugly source.
Currently using unofficial sources until we get better API access.
"""

from ..user.auth import UserKey
from ..user.info import StudentInfo
from pydantic import parse_raw_as
from ..plan.plan import PseudoCourse
from prisma import Json
from .siding import translate as siding
from ..plan.validation.curriculum.tree import Curriculum, CurriculumSpec
from ..plan.courseinfo import clear_course_info_cache, course_info
from . import buscacursos_dl
from prisma.models import (
    Curriculum as DbCurriculum,
    PlanRecommendation as DbPlanRecommendation,
)
import json
from pydantic.json import pydantic_encoder

# from .siding import translate as siding_translate


async def run_upstream_sync():
    """
    Populate database with "official" data.
    """
    print("syncing database with external sources...")
    # Get course data from "official" source
    # Currently we have no official source
    await buscacursos_dl.fetch_to_database()
    # Fetch major, minor and title offer to database
    await siding.load_siding_offer_to_database()
    # Recache course info
    clear_course_info_cache()
    await course_info()


async def get_curriculum(spec: CurriculumSpec) -> Curriculum:
    """
    Get the curriculum definition for a given spec.
    In other words, fetch the full curriculum corresponding to a given
    cyear-major-minor-title combination.
    Note that currently when there is no major/minor selected, an empty curriculum is
    returned.
    Currently, these have to be requested from SIDING, so some caching is performed.
    """

    # The underlying SIDING webservice does not support empty major/minor selections
    if spec.major is None or spec.minor is None:
        return Curriculum(nodes=[])

    db_curr = await DbCurriculum.prisma().find_unique(
        where={
            "cyear_major_minor_title": {
                "cyear": str(spec.cyear),
                "major": spec.major or "",
                "minor": spec.minor or "",
                "title": spec.title or "",
            }
        }
    )
    if db_curr is None:
        courseinfo = await course_info()
        curr = await siding.fetch_curriculum(courseinfo, spec)
        await DbCurriculum.prisma().query_raw(
            """
            INSERT INTO "Curriculum"
                (cyear, major, minor, title, curriculum)
            VALUES($1, $2, $3, $4, $5)
            ON CONFLICT (cyear, major, minor, title)
            DO UPDATE SET curriculum = $5
            """,
            str(spec.cyear),
            spec.major or "",
            spec.minor or "",
            spec.title or "",
            Json(curr.json()),
        )
        return curr
    else:
        return Curriculum.parse_raw(db_curr.curriculum)


async def get_recommended_plan(spec: CurriculumSpec) -> list[list[PseudoCourse]]:
    """
    Fetch the ideal recommended plan for a given curriculum spec.
    In other words, transform a cyear-major-minor-title combination into a list of
    semesters with the ideal course order.
    Note that currently when there is no major/minor selected, no courses are
    recommended.
    Currently, these have to be requested from SIDING, so some caching is performed.
    """

    # The underlying SIDING webservice does not support empty major/minor selections
    if spec.major is None or spec.minor is None:
        return []

    db_plan = await DbPlanRecommendation.prisma().find_unique(
        where={
            "cyear_major_minor_title": {
                "cyear": str(spec.cyear),
                "major": spec.major or "",
                "minor": spec.minor or "",
                "title": spec.title or "",
            }
        }
    )
    if db_plan is None:
        courseinfo = await course_info()
        plan = await siding.fetch_recommended_courses(courseinfo, spec)
        await DbPlanRecommendation.prisma().query_raw(
            """
            INSERT INTO "PlanRecommendation"
                (cyear, major, minor, title, recommended_plan)
            VALUES($1, $2, $3, $4, $5)
            ON CONFLICT (cyear, major, minor, title)
            DO UPDATE SET recommended_plan = $5
            """,
            str(spec.cyear),
            spec.major or "",
            spec.minor or "",
            spec.title or "",
            Json(json.dumps(plan, default=pydantic_encoder)),
        )
        return plan
    else:
        return parse_raw_as(list[list[PseudoCourse]], db_plan.recommended_plan)


async def fetch_student_info(user: UserKey) -> StudentInfo:
    """
    Get the basic student info associated with the given RUT.
    Note that the resulting information may be sensitive.
    """
    return await siding.fetch_student_info(user.rut)


async def fetch_student_previous_courses(
    user: UserKey, info: StudentInfo
) -> list[list[PseudoCourse]]:
    """
    Get the courses that a student has done previously.
    """
    return await siding.fetch_student_previous_courses(user.rut, info)
