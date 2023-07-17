from app import sync
from app.database import prisma
from app.plan.courseinfo import (
    course_info,
)
from app.settings import settings


# Run upstream sync on startup
async def sync_and_cache_curricular_data():
    # Connect with the database
    await prisma.connect()

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

    # Disconnect from the database
    await prisma.disconnect()


if __name__ == "__main__":
    import asyncio

    print("Running startup script...")
    asyncio.run(sync_and_cache_curricular_data())
