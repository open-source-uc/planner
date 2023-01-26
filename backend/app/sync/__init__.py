"""
Update local database with an official but ugly source.
Currently using unofficial sources until we get better API access.
"""

from pydantic import parse_raw_as
from ..plan.plan import PseudoCourse
from prisma import Json
from .siding.translate import (
    fetch_curriculum_from_siding,
    fetch_recommended_courses_from_siding,
)
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
    # TODO: Update to new siding API
    # await siding_translate.load_offer_to_database()
    # Recache course info
    clear_course_info_cache()
    await course_info()


async def get_curriculum(spec: CurriculumSpec) -> Curriculum:
    db_curr = await DbCurriculum.prisma().find_unique(
        where={
            "cyear_major_minor_title": {
                "cyear": spec.cyear,
                "major": spec.major or "",
                "minor": spec.minor or "",
                "title": spec.title or "",
            }
        }
    )
    if db_curr is None:
        courseinfo = await course_info()
        curr = await fetch_curriculum_from_siding(courseinfo, spec)
        await DbCurriculum.prisma().query_raw(
            """
            INSERT INTO "Curriculum"
                (cyear, major, minor, title, curriculum)
            VALUES($1, $2, $3, $4, $5)
            ON CONFLICT (cyear, major, minor, title)
            DO UPDATE SET curriculum = $5
            """,
            spec.cyear,
            spec.major or "",
            spec.minor or "",
            spec.title or "",
            Json(curr.json()),
        )
        return curr
    else:
        return Curriculum.parse_raw(db_curr.curriculum)


async def get_recommended_plan(spec: CurriculumSpec) -> list[list[PseudoCourse]]:
    db_plan = await DbPlanRecommendation.prisma().find_unique(
        where={
            "cyear_major_minor_title": {
                "cyear": spec.cyear,
                "major": spec.major or "",
                "minor": spec.minor or "",
                "title": spec.title or "",
            }
        }
    )
    if db_plan is None:
        courseinfo = await course_info()
        plan = await fetch_recommended_courses_from_siding(courseinfo, spec)
        await DbPlanRecommendation.prisma().query_raw(
            """
            INSERT INTO "PlanRecommendation"
                (cyear, major, minor, title, recommended_plan)
            VALUES($1, $2, $3, $4, $5)
            ON CONFLICT (cyear, major, minor, title)
            DO UPDATE SET recommended_plan = $5
            """,
            spec.cyear,
            spec.major or "",
            spec.minor or "",
            spec.title or "",
            Json(json.dumps(plan, default=pydantic_encoder)),
        )
        return plan
    else:
        return parse_raw_as(list[list[PseudoCourse]], db_plan.recommended_plan)
