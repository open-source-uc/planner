from app import sync
from app.database import prisma
from app.plan.courseinfo import (
    course_info,
)
from app.settings import settings
from app.sync.siding.client import client
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
                courseinfo=settings.autosync_courseinfo,
            )
            # Auto-sync database if empty
            courseinfo = await course_info()
            offer_sample = await DbMajor.prisma().find_first()
            await sync.run_upstream_sync(
                courses=len(courseinfo.courses) == 0,
                curriculums=False,
                offer=offer_sample is None,
                courseinfo=False,
            )
        finally:
            if client.soap_client:
                client.on_shutdown()


if __name__ == "__main__":
    import asyncio

    print("Running startup script...")
    asyncio.run(sync_and_cache_curricular_data())
