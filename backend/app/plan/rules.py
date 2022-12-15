"""
Provide course rules from the course database.
"""

import pydantic
from .logic import Expr
from .validate import Course, CourseRules
from .simplify import simplify
from prisma.models import Course as DbCourse


_course_rules_cache = None


def clear_course_rules_cache():
    global _course_rules_cache
    _course_rules_cache = None


async def course_rules() -> CourseRules:
    if _course_rules_cache is not None:
        return _course_rules_cache

    # Derive course rules from courses in database
    print("building course rules from database...")
    courses = {}
    for course in await DbCourse.prisma().find_many():
        # Parse and validate dep json
        deps = pydantic.parse_raw_as(Expr, course.deps)
        deps = simplify(deps)
        # Create course object
        courses[course.code] = Course(
            code=course.code, credits=course.credits, requires=deps
        )
    print(f"  processed {len(courses)} courses")
    return CourseRules(courses=courses)
