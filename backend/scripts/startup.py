from app import sync
from app.database import prisma
from app.settings import settings
from app.sync.siding.client import client
from prisma.models import CachedCurriculum as DbCachedCurriculum
from prisma.models import Course as DbCourse


# Run upstream sync on startup
async def sync_and_cache_curricular_data():
    async with prisma:
        client.on_startup()
        try:
            # Auto-sync database if empty
            course_sample = await DbCourse.prisma().find_first()
            curriculum_sample = await DbCachedCurriculum.prisma().find_first()
            # Autosync courses if enabled
            await sync.run_upstream_sync(
                courses=settings.autosync_courses or course_sample is None,
                curriculums=settings.autosync_curriculums or curriculum_sample is None,
                packedcourses=settings.autosync_packedcourses,
            )
        finally:
            if client.soap_client:
                client.on_shutdown()


if __name__ == "__main__":
    import asyncio

    print("Running startup script...")
    asyncio.run(sync_and_cache_curricular_data())
