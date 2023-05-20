"""
Cache course info from the database in memory, for easy access.
"""

from dataclasses import dataclass
from typing import Optional
from .course import EquivalenceId, PseudoCourse
import pydantic
from pydantic import BaseModel
from .validation.courses.logic import Expr
from prisma.models import Course, Equivalence, EquivalenceCourse


class CourseDetails(BaseModel):
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


class EquivDetails(BaseModel):
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
    async def from_db(db: Equivalence) -> "EquivDetails":
        dbcourses = await EquivalenceCourse.prisma().find_many(
            where={
                "equiv_code": db.code,
            }
        )
        courses = list(map(lambda ec: ec.course_code, dbcourses))
        return EquivDetails(
            code=db.code,
            name=db.name,
            is_homogeneous=db.is_homogeneous,
            courses=courses,
        )


@dataclass
class CourseInfo:
    courses: dict[str, CourseDetails]
    equivs: dict[str, EquivDetails]

    def try_course(self, code: str) -> Optional[CourseDetails]:
        return self.courses.get(code)

    def try_equiv(self, code: str) -> Optional[EquivDetails]:
        return self.equivs.get(code)

    def is_course_available(self, code: str) -> bool:
        info = self.try_course(code)
        if info is None:
            return False
        return info.is_available

    def get_credits(self, course: PseudoCourse) -> Optional[int]:
        if isinstance(course, EquivalenceId):
            return course.credits
        else:
            info = self.try_course(course.code)
            if info is None:
                return None
            return info.credits


_course_info_cache: Optional[CourseInfo] = None


def clear_course_info_cache():
    global _course_info_cache
    _course_info_cache = None


async def add_equivalence(equiv: EquivDetails):
    print(f"adding equivalence {equiv.code}")
    # Add equivalence to database
    await Equivalence.prisma().query_raw(
        """
        INSERT INTO "Equivalence" (code, name, is_homogeneous)
        VALUES($1, $2, $3)
        ON CONFLICT (code)
        DO UPDATE SET name = $2, is_homogeneous = $3
        """,
        equiv.code,
        equiv.name,
        equiv.is_homogeneous,
    )
    # Add equivalence courses to database
    value_tuples: list[str] = []
    query_args = [equiv.code]
    for i, code in enumerate(equiv.courses):
        value_tuples.append(f"($1, ${2+i})")
        query_args.append(code)
    await EquivalenceCourse.prisma().query_raw(
        f"""
        INSERT INTO "EquivalenceCourse" (equiv_code, course_code)
        VALUES {','.join(value_tuples)}
        ON CONFLICT (equiv_code, course_code)
        DO NOTHING
        """,
        *query_args,
    )
    # Update in-memory cache if it was already loaded
    if _course_info_cache:
        _course_info_cache.equivs[equiv.code] = equiv


async def course_info() -> CourseInfo:
    global _course_info_cache
    if _course_info_cache is None:
        # Derive course rules from courses in database
        print("caching courseinfo from database...")
        print("  fetching courses from database...")
        all_courses = await Course.prisma().find_many()
        print("  loading courses to memory...")
        courses: dict[str, CourseDetails] = {}
        for course in all_courses:
            # Create course object
            courses[course.code] = CourseDetails.from_db(course)
        print(f"  processed {len(courses)} courses")
        print("  loading equivalences from database...")
        all_equivs = await Equivalence.prisma().find_many()
        equivs: dict[str, EquivDetails] = {}
        for equiv in all_equivs:
            equivs[equiv.code] = await EquivDetails.from_db(equiv)
        print(f"  processed {len(equivs)} equivalences")
        _course_info_cache = CourseInfo(courses=courses, equivs=equivs)

    return _course_info_cache
