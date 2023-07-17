import asyncio

from fastapi import APIRouter
from prisma.models import (
    Major as DbMajor,
)
from prisma.models import (
    Minor as DbMinor,
)
from prisma.models import (
    Title as DbTitle,
)
from pydantic import BaseModel

router = APIRouter(prefix="/offer")


@router.get("/major", response_model=list[DbMajor])
async def get_majors(cyear: str):
    """
    Get all the available majors for a given curriculum version (cyear).
    """
    return await DbMajor.prisma().find_many(
        where={
            "cyear": cyear,
        },
    )


@router.get("/minor", response_model=list[DbMinor])
async def get_minors(cyear: str, major_code: str | None = None):
    if major_code is None:
        return await DbMinor.prisma().find_many(
            where={
                "cyear": cyear,
            },
        )
    return await DbMinor.prisma().query_raw(
        """
        SELECT *
        FROM "Minor", "MajorMinor"
        WHERE "MajorMinor".minor = "Minor".code
            AND "MajorMinor".major = $2
            AND "MajorMinor".cyear = $1
            AND "Minor".cyear = $1
        """,
        cyear,
        major_code,
    )


@router.get("/title", response_model=list[DbTitle])
async def get_titles(cyear: str):
    return await DbTitle.prisma().find_many(
        where={
            "cyear": cyear,
        },
    )


class FullOffer(BaseModel):
    majors: list[DbMajor]
    minors: list[DbMinor]
    titles: list[DbTitle]


@router.get("/", response_model=FullOffer)
async def get_offer(cyear: str, major_code: str | None = None):
    majors, minors, titles = await asyncio.gather(
        get_majors(cyear),
        get_minors(cyear, major_code),
        get_titles(cyear),
    )
    return FullOffer(majors=majors, minors=minors, titles=titles)
