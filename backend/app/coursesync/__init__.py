"""
Update local course database with an official but ugly source.
Currently using an unofficial source until we get better API access.
"""

from functools import lru_cache
from prisma import Base64
from .bcscrape import fetch_and_translate
from prisma.models import CourseRules as DbCourseRules
from ..validate.models import CourseRules
import bz2


@lru_cache
async def universal_course_rules() -> CourseRules:
    rules = await DbCourseRules.prisma().find_unique(where={"id": "universal"})
    if rules is None:
        rules = await run_course_sync()
    else:
        rules = rules.rules.decode()
    return CourseRules.parse_raw(bz2.decompress(rules))


async def run_course_sync():
    print("running course synchronization...")
    course_rules = fetch_and_translate()
    compressed = bz2.compress(course_rules.json().encode("UTF-8"))
    encoded = Base64.encode(compressed)
    await DbCourseRules.prisma().upsert(
        where={"id": "universal"},
        data={
            "create": {"id": "universal", "rules": encoded},
            "update": {"rules": encoded},
        },
    )
    # This method triggers a pyright warning, even though it is completely correct
    universal_course_rules.cache_clear()  # pyright: reportFunctionMemberAccess = false
    print("  finished synchronizing courses")
    return compressed
