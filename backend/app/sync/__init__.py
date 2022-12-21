"""
Update local database with an official but ugly source.
Currently using unofficial sources until we get better API access.
"""

from ..validation.courseinfo import clear_course_info_cache, course_info
from . import bcscrape, example_curriculums


async def run_upstream_sync():
    """
    Populate database with "official" data.
    """
    print("syncing database with external sources...")
    # Get course data from "official" source
    # Currently we have no official source
    await bcscrape.fetch_to_database()
    # Get curriculum data from "official" source
    # Currently we have no official source
    await example_curriculums.load_to_database()
    # Recache course info
    clear_course_info_cache()
    await course_info()
