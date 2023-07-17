"""
Cache course info from the database in memory, for easy access.
"""

from dataclasses import dataclass

import pydantic
from prisma.models import (
    CachedCourseInfo as DbCachedCourseInfo,
)
from prisma.models import (
    Course,
    Equivalence,
    EquivalenceCourse,
)
from pydantic import BaseModel
from unidecode import unidecode

from app.plan.course import EquivalenceId, PseudoCourse
from app.plan.validation.courses.logic import Expr

_CACHED_COURSES_ID: str = "cached-course-info"


class CourseDetails(BaseModel):
    # The unique code identifying this course.
    code: str
    # An informative, short course name.
    name: str
    # The nonnegative amount of credits.
    credits: int
    # The requirements that must be true in order to take this course.
    deps: Expr
    # The list of courses that are equivalent to this course (in terms of requirements).
    # Taking this course is equivalent to having taken any course in this list.
    banner_equivs: list[str]
    # For old course codes that were replaced by equivalent courses, this is hopefully
    # the code of that newer course.
    # For valid, relevant courses that are still available for students to take, this
    # is the same as `code`.
    canonical_equiv: str
    # The course program.
    # A long, textual description.
    program: str
    # "Facultad" that teaches the course.
    school: str
    # "Area de Formacion General"?
    area: str | None
    category: str | None
    # Heuristic indicating if the course is still available for students to take.
    is_available: bool
    # Booleans indicating on what semesters is the course available.
    # First semester (odd semesters), second semester (even semesters) (including TAV)
    semestrality: tuple[bool, bool]

    @staticmethod
    def from_db(db: Course) -> "CourseDetails":
        # Parse and validate dep json
        deps = pydantic.parse_raw_as(Expr, db.deps)
        return CourseDetails(
            code=db.code,
            name=db.name,
            credits=db.credits,
            deps=deps,
            banner_equivs=db.banner_equivs,
            canonical_equiv=db.canonical_equiv,
            program=db.program,
            school=db.school,
            area=db.area,
            category=db.category,
            is_available=db.is_available,
            semestrality=(
                db.semestrality_first,
                db.semestrality_second,
            ),
        )


class EquivDetails(BaseModel):
    """
    Details about an equivalence.
    - code: Unique code identifying this equivalence.
        Unique across course and equivalence codes (ie. course and equivalence names
        live in the same namespace).
    - name: Informative name of this equivalence.
    - is_homogeneous: Indicates whether this equivalence is "homogeneous".
        A homogeneous equivalence is one where all of its concrete courses have the
        same requirements and reverse requirements (eg. "Dinamica" is homogeneous, but
        "OFG" is not).
        The requirement validator gives up on non-homogeneous equivalences, but tries
        to validate homogeneous dependencies.
    - is_unessential: Whether the equivalence can go unspecified without raising an
        error.
    - courses: List of concrete course codes that make up this equivalence.
    """

    code: str
    name: str
    is_homogeneous: bool
    is_unessential: bool
    courses: list[str]

    @staticmethod
    async def from_db(db: Equivalence) -> "EquivDetails":
        dbcourses = await EquivalenceCourse.prisma().find_many(
            where={
                "equiv_code": db.code,
            },
            order={
                "index": "asc",
            },
        )
        courses = [ec.course_code for ec in dbcourses]
        return EquivDetails(
            code=db.code,
            name=db.name,
            is_homogeneous=db.is_homogeneous,
            is_unessential=db.is_unessential,
            courses=courses,
        )


@dataclass
class CourseInfo:
    courses: dict[str, CourseDetails]
    equivs: dict[str, EquivDetails]

    def try_course(self, code: str) -> CourseDetails | None:
        return self.courses.get(code)

    def try_equiv(self, code: str) -> EquivDetails | None:
        return self.equivs.get(code)

    def try_any(self, course: PseudoCourse) -> CourseDetails | EquivDetails | None:
        return (
            self.try_equiv(course.code)
            if isinstance(course, EquivalenceId)
            else self.try_course(course.code)
        )

    def get_credits(self, course: PseudoCourse) -> int | None:
        if isinstance(course, EquivalenceId):
            return course.credits
        info = self.try_course(course.code)
        if info is None:
            return None
        return info.credits

    def get_ghost_credits(self, course: PseudoCourse) -> int | None:
        """
        Like `get_credits` but 0-credit courses return 1 instead.
        """
        creds = self.get_credits(course)
        return 1 if creds == 0 else creds


_course_info_cache: CourseInfo | None = None


async def clear_course_info_cache():
    global _course_info_cache
    _course_info_cache = None
    await DbCachedCourseInfo.prisma().delete(where={"id": _CACHED_COURSES_ID})


async def add_equivalence(equiv: EquivDetails):
    print(f"adding equivalence {equiv.code}")
    # Add equivalence to database
    await Equivalence.prisma().query_raw(
        """
        INSERT INTO "Equivalence" (code, name, is_homogeneous, is_unessential)
        VALUES($1, $2, $3, $4)
        ON CONFLICT (code)
        DO UPDATE SET name = $2, is_homogeneous = $3, is_unessential = $4
        """,
        equiv.code,
        equiv.name,
        equiv.is_homogeneous,
        equiv.is_unessential,
    )
    # Clear previous equivalence courses
    await EquivalenceCourse.prisma().delete_many(where={"equiv_code": equiv.code})
    # Add equivalence courses to database
    value_tuples: list[str] = []
    query_args = [equiv.code]
    for i, code in enumerate(equiv.courses):
        value_tuples.append(
            f"({i}, $1, ${2+i})",
        )  # NOTE: No user-input is injected here
        query_args.append(code)
    assert value_tuples
    await EquivalenceCourse.prisma().query_raw(
        f"""
        INSERT INTO "EquivalenceCourse" (index, equiv_code, course_code)
        VALUES {','.join(value_tuples)}
        ON CONFLICT
        DO NOTHING
        """,  # noqa: S608 (only numbers are inserted in string)
        *query_args,
    )
    # Update in-memory cache if it was already loaded
    if _course_info_cache:
        _course_info_cache.equivs[equiv.code] = equiv


class CachedCourseDetailsJson(BaseModel):
    __root__: dict[str, CourseDetails]


async def course_info() -> CourseInfo:
    # TODO: Check in with the central database every so often
    # This would allow us to run multiple instances
    global _course_info_cache
    if _course_info_cache is None:
        # Derive course rules from courses in database
        print("caching courseinfo from database...")
        courses: dict[str, CourseDetails]

        # Attempt to fetch pre-parsed courses
        preparsed = await DbCachedCourseInfo.prisma().find_unique(
            {"id": _CACHED_COURSES_ID},
        )
        if preparsed is not None:
            print("  loading pre-parsed course cache...")
            courses = pydantic.parse_raw_as(dict[str, CourseDetails], preparsed.info)
        else:
            # Parse courses from database
            print("  fetching courses from database...")
            all_courses = await Course.prisma().find_many()
            print("  loading courses to memory...")
            courses = {}
            for course in all_courses:
                # Create course object
                courses[course.code] = CourseDetails.from_db(course)
            print("  storing cached courses to database")
            await DbCachedCourseInfo.prisma().create(
                {
                    "id": _CACHED_COURSES_ID,
                    "info": CachedCourseDetailsJson(__root__=courses).json(),
                },
            )
        print(f"  processed {len(courses)} courses")

        # Load equivalences
        print("  loading equivalences from database...")
        all_equivs = await Equivalence.prisma().find_many()
        equivs: dict[str, EquivDetails] = {}
        for equiv in all_equivs:
            equivs[equiv.code] = await EquivDetails.from_db(equiv)
        print(f"  processed {len(equivs)} equivalences")

        _course_info_cache = CourseInfo(courses=courses, equivs=equivs)

    return _course_info_cache


def make_searchable_name(name: str) -> str:
    """
    Take a course name and normalize it to lowercase english letters, numbers and
    spaces.
    """
    name = unidecode(name)  # Remove accents
    name = name.lower()  # Make lowercase
    name = "".join(
        char if char.isalnum() else " " for char in name
    )  # Remove non-alphanumeric characters
    return " ".join(name.split())  # Merge adjacent spaces
