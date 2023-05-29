"""
Update local database with an official but ugly source.
Currently using unofficial sources until we get better API access.
"""

from collections import OrderedDict
import time

from ..settings import settings
from ..user.auth import UserKey
from ..user.info import StudentContext
from prisma import Json
from .siding import translate as siding_translate
from ..plan.validation.curriculum.tree import Curriculum, CurriculumSpec
from ..plan.courseinfo import clear_course_info_cache, course_info
from . import buscacursos_dl
from prisma.models import (
    Curriculum as DbCurriculum,
    Major as DbMajor,
    Minor as DbMinor,
    Title as DbTitle,
    MajorMinor as DbMajorMinor,
    EquivalenceCourse as DbEquivalenceCourse,
    Course as DbCourse,
    Equivalence as DbEquivalence,
)


async def clear_upstream_data(courses: bool = True, offer: bool = True):
    print("  clearing upstream data from database")
    await DbEquivalenceCourse.prisma().delete_many()
    await DbEquivalence.prisma().delete_many()
    if courses:
        await DbCourse.prisma().delete_many()

    if offer:
        await DbMajor.prisma().delete_many()
        await DbMinor.prisma().delete_many()
        await DbTitle.prisma().delete_many()
        await DbMajorMinor.prisma().delete_many()

    await DbCurriculum.prisma().delete_many()


async def run_upstream_sync(courses: bool = True, offer: bool = True):
    """
    Populate database with "official" data.
    """
    print("syncing database with external sources...")
    # Remove previous data
    await clear_upstream_data(courses, offer)
    if courses:
        # Get course data from "official" source
        # Currently we have no official source
        await buscacursos_dl.fetch_to_database()
    # Fetch major, minor and title offer to database
    if offer:
        await siding_translate.load_siding_offer_to_database()
    # Recache course info
    await clear_course_info_cache()
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
        return Curriculum.empty()

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
