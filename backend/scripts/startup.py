from app import sync
from app.database import prisma
from app.plan.courseinfo import (
    course_info,
)
from app.settings import settings
from app.sync.siding.client import client


# Run upstream sync on startup
async def sync_and_cache_curricular_data():
    async with prisma:
        client.on_startup()
        try:
            # Sync courses if database is empty
            await sync.run_upstream_sync(
                courses=settings.autosync_courses,
                curriculums=settings.autosync_curriculums,
                offer=settings.autosync_offer,
                courseinfo=settings.autosync_courseinfo,
            )
            # Prime course info cache
            courseinfo = await course_info()
            if not courseinfo.courses:
                # Auto-sync database if there are no courses
                await sync.run_upstream_sync(
                    courses=True,
                    curriculums=False,
                    offer=False,
                    courseinfo=False,
                )
        finally:
            if client.soap_client:
                client.on_shutdown()


if __name__ == "__main__":
    import asyncio

    print("Running startup script...")
    asyncio.run(sync_and_cache_curricular_data())
