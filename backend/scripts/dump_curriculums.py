"""
Debug tool to dump the curriculum definitions out of the database.
The startup script must have been run before.
"""

from app.database import prisma
from prisma.models import CachedCurriculum as DbCachedCurriculum


async def collate():
    async with prisma:
        plans = await DbCachedCurriculum.prisma().find_first_or_raise()
        print(plans.curriculums)


if __name__ == "__main__":
    import asyncio

    asyncio.run(collate())
