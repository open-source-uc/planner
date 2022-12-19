"""
Update local course database with an official but ugly source.
Currently using an unofficial source until we get better API access.
"""

from ..validation.courseinfo import clear_course_info_cache, course_info
from .bcscrape import fetch_to_database


async def run_course_sync():
    """
    Populate database with course data.
    """
    print("running course sync...")
    # Get data from "official" source
    await fetch_to_database()
    # Recache course info
    clear_course_info_cache()
    await course_info()
