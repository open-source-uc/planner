"""
Debug tool to dump the curriculum definitions out of the database.
The startup script must have been run before.
"""

from app.database import prisma
from app.sync.database import CURRICULUMS_PACK_ID, load_packed


async def collate():
    async with prisma:
        packed = await load_packed(CURRICULUMS_PACK_ID)
        print(packed)


if __name__ == "__main__":
    import asyncio

    asyncio.run(collate())
