import logging

from app.database import prisma
from app.logger import setup_logger
from app.plan.courseinfo import course_info
from app.plan.generation import generate_empty_plan, generate_recommended_plan
from app.plan.validation.curriculum.tree import (
    CurriculumSpec,
    Cyear,
    MajorCode,
    MinorCode,
    TitleCode,
)
from prisma.models import Major, MajorMinor, Minor, Title


async def test_all_plans():
    setup_logger()

    async with prisma:
        await course_info()

        logging.info("collecting all curriculum combinations")
        all_specs: list[CurriculumSpec] = []
        cyears: set[str] = set()
        for major in await Major.prisma().find_many():
            cyears.add(major.cyear)
        for cyear in cyears:
            dbmajors = await Major.prisma().find_many(where={"cyear": cyear})
            majors: list[MajorCode | None] = [
                MajorCode(major.code) for major in dbmajors
            ]
            majors.append(None)

            dbminors = await Minor.prisma().find_many(where={"cyear": cyear})
            allminors: list[MinorCode | None] = [
                MinorCode(minor.code) for minor in dbminors
            ]
            allminors.append(None)

            dbtitles = await Title.prisma().find_many(where={"cyear": cyear})
            alltitles: list[TitleCode | None] = [
                TitleCode(title.code) for title in dbtitles
            ]
            alltitles.append(None)

            for major in majors:
                minors: list[MinorCode | None]
                if major is None:
                    minors = allminors
                else:
                    dbassocs = await MajorMinor.prisma().find_many(
                        where={"cyear": cyear, "major": major},
                    )
                    minors = [MinorCode(assoc.minor) for assoc in dbassocs]
                    minors.append(None)
                for minor in minors:
                    for title in alltitles:
                        # Try this cyear-major-minor-title
                        all_specs.append(
                            CurriculumSpec(
                                cyear=Cyear.parse_obj({"raw": cyear}),
                                major=major,
                                minor=minor,
                                title=title,
                            ),
                        )

        logging.info(f"generating {len(all_specs)} combinations")
        ok = 0
        failed: list[CurriculumSpec] = []
        for spec in all_specs:
            # Generate!
            try:
                logging.info(f"testing {spec}")
                plan = await generate_empty_plan(None)
                plan.curriculum = spec
                plan = await generate_recommended_plan(plan, None)
                assert plan.classes and any(plan.classes)
                ok += 1
            except Exception as e:
                logging.exception(e)
                failed.append(spec)

        logging.info(f"tested all {len(all_specs)} combinations")
        logging.info(f"{ok}/{len(all_specs)} ok")
        if failed:
            logging.info("failed:")
            for spec in failed:
                logging.info(f"    {spec}")


if __name__ == "__main__":
    import asyncio

    print("testing all curriculums...")
    asyncio.run(test_all_plans())
