"""
Update local course database with an official but ugly source.
Currently using an unofficial source until we get better API access.
"""

from ..validate.rules import clear_course_rules_cache, course_rules
from .bcscrape import fetch_to_database


async def run_course_sync():
    """
    Populate database with course data.
    """
    print("running course sync...")
    # Get data from "official" source
    await fetch_to_database()
    # Recalculate course rules
    clear_course_rules_cache()
    await course_rules()
