"""
Cache course info from the database in memory, for easy access.
"""

from dataclasses import dataclass
from typing import Optional
import pydantic
from .validation.courses.logic import Expr
from prisma.models import Course


@dataclass
class CourseInfo:
    code: str
    name: str
    credits: int
    deps: Expr
    program: str
    school: str
    area: Optional[str]
    category: Optional[str]


_course_info_cache: Optional[dict[str, CourseInfo]] = None


def clear_course_info_cache():
    global _course_info_cache
    _course_info_cache = None


async def course_info() -> dict[str, CourseInfo]:
    global _course_info_cache
    if _course_info_cache is None:
        # Derive course rules from courses in database
        print("caching course data from database...")
        courses = {}
        for course in await Course.prisma().find_many():
            # Parse and validate dep json
            deps = pydantic.parse_raw_as(Expr, course.deps)
            # deps = simplify(deps)
            # Create course object
            courses[course.code] = CourseInfo(
                code=course.code,
                name=course.name,
                credits=course.credits,
                deps=deps,
                program=course.program,
                school=course.school,
                area=course.area,
                category=course.category,
            )
        print(f"  processed {len(courses)} courses")
        _course_info_cache = courses

    return _course_info_cache
