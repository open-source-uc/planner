import logging

from app.database import prisma
from app.settings import settings
from app.sync.database import (
    COURSEDATA_PACK_ID,
    CURRICULUMS_PACK_ID,
    NoPackedDataError,
    load_packed,
    sync_from_external_sources,
)
from app.sync.siding.client import client


# Run upstream sync on startup
async def sync_and_cache_curricular_data():
    logging.basicConfig()
    async with prisma:
        client.on_startup()
        try:
            # Determine if coursedata is empty
            coursedata_empty = False
            try:
                await load_packed(COURSEDATA_PACK_ID)
            except NoPackedDataError:
                coursedata_empty = True

            # Determine if curriculum data is empty
            curriculums_empty = False
            try:
                await load_packed(CURRICULUMS_PACK_ID)
            except NoPackedDataError:
                curriculums_empty = True

            # Autosync courses if enabled
            await sync_from_external_sources(
                sync_coursedata=settings.autosync_courses or coursedata_empty,
                sync_curriculum=settings.autosync_curriculums or curriculums_empty,
            )
        finally:
            if client.soap_client:
                client.on_shutdown()


if __name__ == "__main__":
    import asyncio

    print("Running startup script...")
    asyncio.run(sync_and_cache_curricular_data())
