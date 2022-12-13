"""
Update local course database with an official but ugly source.
Currently using an unofficial source until we get better API access.
"""

from prisma import Base64
from .bcscrape import fetch_and_translate
from prisma.models import CourseRules as DbCourseRules
from ..validate.models import CourseRules
import bz2

_universal_rules_cache = None


async def universal_course_rules() -> CourseRules:
    global _universal_rules_cache
    if _universal_rules_cache is not None:
        return _universal_rules_cache
    rules = await DbCourseRules.prisma().find_unique(where={"id": "universal"})
    if rules is None:
        rules = await run_course_sync()
    else:
        rules = rules.rules.decode()
    rules = CourseRules.parse_raw(bz2.decompress(rules))
    _universal_rules_cache = rules
    return rules


def postprocess_courses(rules: CourseRules):
    print("  postprocessing courses...")
    for code, course in rules.courses.items():
        if code == "MAT1203":
            print(f"before simplify: {course.requires}")
        course.requires = course.requires.simplify()
        if code == "MAT1203":
            print(f"after simplify: {course.requires}")


async def run_course_sync():
    global _universal_rules_cache
    print("running course synchronization...")
    course_rules = fetch_and_translate()
    postprocess_courses(course_rules)
    print("  saving to database...")
    compressed = bz2.compress(course_rules.json().encode("UTF-8"))
    encoded = Base64.encode(compressed)
    await DbCourseRules.prisma().upsert(
        where={"id": "universal"},
        data={
            "create": {"id": "universal", "rules": encoded},
            "update": {"rules": encoded},
        },
    )
    _universal_rules_cache = None
    print("  finished synchronizing courses")
    return compressed
