from app import sync
from app.database import prisma
from app.settings import settings
from app.sync.siding.client import client
from prisma.models import CachedCurriculum as DbCachedCurriculum
from prisma.models import Course as DbCourse
from prisma.models import Major as DbMajor


# Run upstream sync on startup
async def sync_and_cache_curricular_data():
    async with prisma:
        client.on_startup()
        try:
            # Autosync courses if enabled
            await sync.run_upstream_sync(
                courses=settings.autosync_courses,
                curriculums=settings.autosync_curriculums,
                offer=settings.autosync_offer,
                packedcourses=settings.autosync_packedcourses,
            )
            # Auto-sync database if empty
            course_sample = await DbCourse.prisma().find_first()
            offer_sample = await DbMajor.prisma().find_first()
            curriculum_sample = await DbCachedCurriculum.prisma().find_first()
            await sync.run_upstream_sync(
                courses=course_sample is None,
                curriculums=curriculum_sample is None,
                offer=offer_sample is None,
                packedcourses=False,
            )
        finally:
            if client.soap_client:
                client.on_shutdown()


if __name__ == "__main__":
    import asyncio

    print("Running startup script...")
    asyncio.run(sync_and_cache_curricular_data())
