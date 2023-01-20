"""
Update local database with an official but ugly source.
Currently using unofficial sources until we get better API access.
"""

from ..plan.courseinfo import clear_course_info_cache, course_info
from . import buscacursos_dl

# from .siding import translate as siding_translate


async def run_upstream_sync():
    """
    Populate database with "official" data.
    """
    print("syncing database with external sources...")
    # Get course data from "official" source
    # Currently we have no official source
    await buscacursos_dl.fetch_to_database()
    # Fetch major, minor and title offer to database
    # TODO: Update to new siding API
    # await siding_translate.load_offer_to_database()
    # Recache course info
    clear_course_info_cache()
    await course_info()
