"""
Update local database with an official but ugly source.
Currently using unofficial sources until we get better API access.
"""

import time
import traceback
from collections import OrderedDict

from prisma.models import (
    Course as DbCourse,
)
from prisma.models import (
    Curriculum as DbCurriculum,
)
from prisma.models import (
    Equivalence as DbEquivalence,
)
from prisma.models import (
    EquivalenceCourse as DbEquivalenceCourse,
)
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
from pydantic import ValidationError

from ..plan.courseinfo import clear_course_info_cache, course_info
from ..plan.validation.curriculum.tree import (
    Curriculum,
    CurriculumSpec,
)
from ..settings import settings
from ..user.auth import UserKey
from ..user.info import StudentContext
from . import buscacursos_dl
from .siding import translate as siding_translate


async def run_upstream_sync(
    *,
    courses: bool,
    curriculums: bool,
    offer: bool,
    courseinfo: bool,
):
    """
    Populate database with "official" data.
    """

    if curriculums or courses:
        # If we delete courses, we must also delete equivalences (because equivalences
        # reference courses)
        # If we delete equivalences, we must also delete curriculums (because
        # curriculums reference equivalences)

        print("deleting curriculum cache...")
        # Equivalences and curriculums are cached lazily
        # Therefore, we can delete them without refetching them
        await DbEquivalenceCourse.prisma().delete_many()
        await DbEquivalence.prisma().delete_many()
        await DbCurriculum.prisma().delete_many()

    if courses:
        print("syncing course database...")
        # Clear previous courses
        await DbCourse.prisma().delete_many()
        # Get course data from "official" source
        # Currently we have no official source
        await buscacursos_dl.fetch_to_database()

    if offer:
        print("syncing curriculum offer...")
        # Clear available programs
        await DbMajor.prisma().delete_many()
        await DbMinor.prisma().delete_many()
        await DbTitle.prisma().delete_many()
        await DbMajorMinor.prisma().delete_many()
        # Refetch available programs
        await siding_translate.load_siding_offer_to_database()

    if courseinfo or courses:
        # If we updated the courses, we must update the cache too

        print("caching courseinfo...")
        # Recache courseinfo
        await clear_course_info_cache()
        await course_info()


async def _get_curriculum_piece(spec: CurriculumSpec) -> Curriculum:
    """
    Get the curriculum definition for a given spec.
    In other words, fetch the full curriculum corresponding to a given
    cyear-major-minor-title combination.
    Note that currently when there is no major/minor selected, an empty curriculum is
    returned.
    Currently, these have to be requested from SIDING, so some caching is performed.
    """

    db_curr = await DbCurriculum.prisma().find_unique(
        where={
            "cyear_major_minor_title": {
                "cyear": str(spec.cyear),
                "major": spec.major or "",
                "minor": spec.minor or "",
                "title": spec.title or "",
            },
        },
    )
    if db_curr is not None:
        try:
            return Curriculum.parse_raw(db_curr.curriculum)
        except ValidationError:
            print(f"regenerating curriculum for {spec}: failed to parse cache")
            traceback.print_exc()

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
        curr.json(),
    )
    return curr


async def get_curriculum(spec: CurriculumSpec) -> Curriculum:
    out = Curriculum.empty()

    # Fetch major (or common plan)
    major = await _get_curriculum_piece(
        CurriculumSpec(
            cyear=spec.cyear,
            major=spec.major,
            minor=None,
            title=None,
        ),
    )
    out.extend(major)

    # Fetch minor
    if spec.minor is not None:
        minor = await _get_curriculum_piece(
            CurriculumSpec(
                cyear=spec.cyear,
                major=None,
                minor=spec.minor,
                title=None,
            ),
        )
        out.extend(minor)

    # Fetch title
    if spec.title is not None:
        title = await _get_curriculum_piece(
            CurriculumSpec(
                cyear=spec.cyear,
                major=None,
                minor=None,
                title=spec.title,
            ),
        )
        out.extend(title)

    return out


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
    passed, in_course = await siding_translate.fetch_student_previous_courses(
        user.rut,
        info,
    )
    ctx = StudentContext(
        info=info,
        passed_courses=passed,
        current_semester=len(passed) - (1 if in_course else 0),
        next_semester=len(passed),
    )

    # Add to cache and return
    _student_context_cache[user.rut] = (
        ctx,
        time.monotonic() + settings.student_info_expire,
    )
    return ctx
