"""
Update local database with an official but ugly source.
Currently using unofficial sources until we get better API access.
"""

from collections import OrderedDict
import time

from ..settings import settings
from ..user.auth import UserKey
from ..user.info import StudentContext
from pydantic import parse_raw_as
from ..plan.plan import PseudoCourse
from prisma import Json
from .siding import translate as siding_translate
from ..plan.validation.curriculum.tree import Curriculum, CurriculumSpec
from ..plan.courseinfo import clear_course_info_cache, course_info
from . import buscacursos_dl
from prisma.models import (
    Curriculum as DbCurriculum,
    PlanRecommendation as DbPlanRecommendation,
)
import json
from pydantic.json import pydantic_encoder


async def run_upstream_sync():
    """
    Populate database with "official" data.
    """
    print("syncing database with external sources...")
    # Get course data from "official" source
    # Currently we have no official source
    await buscacursos_dl.fetch_to_database()
    # Fetch major, minor and title offer to database
    await siding_translate.load_siding_offer_to_database()
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
        curr = await siding_translate.fetch_curriculum(courseinfo, spec)
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
        plan = await siding_translate.fetch_recommended_courses(courseinfo, spec)
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


_student_context_cache: OrderedDict[str, tuple[StudentContext, float]] = OrderedDict()


async def get_student_data(user: UserKey) -> StudentContext:
    # Use entries in cache
    if user.rut in _student_context_cache:
        return _student_context_cache[user.rut][0]

    # Delete old entries from cache
    now = time.monotonic()
    while _student_context_cache:
        rut, (_ctx, expiration) = next(iter(_student_context_cache.items()))
        if now <= expiration:
            break
        _student_context_cache.pop(rut)

    # Request user context from SIDING
    print(f"fetching user data for student {user.rut} from SIDING...")
    info = await siding_translate.fetch_student_info(user.rut)
    passed = await siding_translate.fetch_student_previous_courses(user.rut, info)
    ctx = StudentContext(info=info, passed_courses=passed)

    # Add to cache and return
    _student_context_cache[user.rut] = (
        ctx,
        time.monotonic() + settings.student_info_expire,
    )
    return ctx
