"""
Cache course info from the database in memory, for easy access.
"""

from dataclasses import dataclass
from typing import Optional
import pydantic
from .validation.courses.logic import Expr
from prisma.models import Course, Equivalence


@dataclass
class CourseDetails:
    code: str
    name: str
    credits: int
    deps: Expr
    program: str
    school: str
    area: Optional[str]
    category: Optional[str]
    is_available: bool
    # First semester, second semester, TAV
    semestrality: tuple[bool, bool, bool]

    @staticmethod
    def from_db(db: Course) -> "CourseDetails":
        # Parse and validate dep json
        deps = pydantic.parse_raw_as(Expr, db.deps)
        # deps = simplify(deps)
        return CourseDetails(
            code=db.code,
            name=db.name,
            credits=db.credits,
            deps=deps,
            program=db.program,
            school=db.school,
            area=db.area,
            category=db.category,
            is_available=db.is_available,
            semestrality=(
                db.semestrality_first,
                db.semestrality_second,
                db.semestrality_tav,
            ),
        )


@dataclass
class EquivDetails:
    code: str
    name: str
    # Indicates whether this equivalence is "homogeneous".
    # A homogeneous equivalence is one where all of its concrete courses have the same
    # requirements and reverse requirements (eg. "Dinamica" is homogeneous, but "OFG"
    # is not).
    # The requirement validator gives up on non-homogeneous equivalences, but tries to
    # validate homogeneous dependencies.
    is_homogeneous: bool
    courses: list[str]

    @staticmethod
    def from_db(db: Equivalence) -> "EquivDetails":
        return EquivDetails(
            code=db.code,
            name=db.name,
            is_homogeneous=db.is_homogeneous,
            courses=db.courses,
        )


@dataclass
class CourseInfo:
    courses: dict[str, CourseDetails]
    equivs: dict[str, EquivDetails]

    def try_course(self, code: str) -> Optional[CourseDetails]:
        return self.courses.get(code)

    def try_equiv(self, code: str) -> Optional[EquivDetails]:
        return self.equivs.get(code)

    def course(self, code: str) -> CourseDetails:
        return self.courses[code]

    def equiv(self, code: str) -> EquivDetails:
        return self.equivs[code]


_course_info_cache: Optional[CourseInfo] = None


def clear_course_info_cache():
    global _course_info_cache
    _course_info_cache = None


async def add_equivalence(equiv: Equivalence):
    print(f"adding equivalence {equiv.code}")
    # Add equivalence to database
    await Equivalence.prisma().create(
        data={
            "code": equiv.code,
            "name": equiv.name,
            "is_homogeneous": equiv.is_homogeneous,
            "courses": equiv.courses,
        },
    )
    # Update in-memory cache if it was already loaded
    if _course_info_cache:
        _course_info_cache.equivs[equiv.code] = EquivDetails.from_db(equiv)


async def course_info() -> CourseInfo:
    global _course_info_cache
    if _course_info_cache is None:
        # Derive course rules from courses in database
        print("caching courseinfo from database...")
        print("  fetching courses from database...")
        all_courses = await Course.prisma().find_many()
        print("  loading courses to memory...")
        courses = {}
        for course in all_courses:
            # Create course object
            courses[course.code] = CourseDetails.from_db(course)
        print(f"  processed {len(courses)} courses")
        print("  loading equivalences from database...")
        all_equivs = await Equivalence.prisma().find_many()
        equivs = {}
        for equiv in all_equivs:
            equivs[equiv.code] = EquivDetails.from_db(equiv)
        print(f"  processed {len(equivs)} equivalences")
        _course_info_cache = CourseInfo(courses=courses, equivs=equivs)

    return _course_info_cache
