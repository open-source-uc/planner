"""
Manage static information about the university.
This information is synced from external sources, and is static for the lifetime of the
webapp. In particular, a prestartup script updates this info before startup.

Currently this info is:
- Course data (currently sourced from buscacursos-dl, which in turn sources from
    catalogo.uc.cl and buscacursos.uc.cl)
- Curriculum data (currently sourced from a mixture of SIDING endpoints and static
    hardcoded data, because the format that SIDING uses is not flexible enough to
    represent the curriculums without involving hardcoded rules)

In the future, this info might also include:
- ECA data (survey-based info about how many hours each course takes)
- RamosUC-based metadata
"""

import logging
from typing import TYPE_CHECKING

import pydantic
from prisma.models import Course as DbCourse
from prisma.models import Equivalence as DbEquivalence
from prisma.models import EquivalenceCourse as DbEquivalenceCourse
from prisma.models import Major as DbMajor
from prisma.models import MajorMinor as DbMajorMinor
from prisma.models import Minor as DbMinor
from prisma.models import PackedData as DbPackedData
from prisma.models import Title as DbTitle

from app.plan.courseinfo import CourseDetails, CourseInfo, EquivDetails
from app.sync import buscacursos_dl
from app.sync.curriculums.collate import collate_plans
from app.sync.curriculums.storage import CurriculumStorage

if TYPE_CHECKING:
    from prisma.types import (
        MajorCreateInput,
        MajorMinorCreateInput,
        MinorCreateInput,
        TitleCreateInput,
    )

log = logging.getLogger("db-sync")


_static_course_info: CourseInfo | None = None
_static_curriculum_storage: CurriculumStorage | None = None


async def course_info() -> CourseInfo:
    if _static_course_info is None:
        raise RuntimeError(
            "attempt to use courseinfo before it is loaded from db",
        )
    return _static_course_info


async def curriculum_storage() -> CurriculumStorage:
    if _static_curriculum_storage is None:
        raise RuntimeError(
            "attempt to use curriculum storage before it is loaded from db",
        )
    return _static_curriculum_storage


COURSEDATA_PACK_ID: str = "course-data"
CURRICULUMS_PACK_ID: str = "curriculum-storage"


async def load_packed_data_from_db():
    global _static_course_info, _static_curriculum_storage

    log.info("loading static data from db to local memory")

    # Load coursedata
    log.info("  fetching packed coursedata from db")
    courses: dict[str, CourseDetails] = pydantic.parse_raw_as(
        dict[str, CourseDetails],
        await load_packed(COURSEDATA_PACK_ID),
    )

    # Load curriculum data
    log.info("  fetching packed curriculum data from db")
    storage: CurriculumStorage = CurriculumStorage.parse_raw(
        await load_packed(CURRICULUMS_PACK_ID),
    )

    # Save courseinfo in RAM
    _static_course_info = CourseInfo(courses=courses, equivs=storage.lists)

    # Save curriculum storage in RAM
    _static_curriculum_storage = storage

    log.info(
        "  loaded %s courses, %s equivalences and %s plans",
        len(courses),
        len(storage.lists),
        len(storage.majors) + len(storage.minors) + len(storage.titles),
    )


async def sync_from_external_sources(sync_coursedata: bool, sync_curriculum: bool):
    if sync_coursedata:
        log.info("syncing coursedata")

        log.info("  clearing courses and equivalences from db")
        await DbEquivalenceCourse.prisma().delete_many()
        await DbEquivalence.prisma().delete_many()
        await DbCourse.prisma().delete_many()

        log.info("  fetching course metadata")
        await buscacursos_dl.fetch_to_database()

        log.info("  updating packed coursedata")
        await _update_packed_coursedata_in_database()

    # If we sync coursedata, we must delete courses from the database
    # If we delete courses from the database, we must delete equivalences (because they
    # reference courses)
    # If we delete equivalences, we must recreate them from curriculum data
    # Therefore, if we sync coursedata, we must sync curriculum
    if sync_curriculum or sync_coursedata:
        log.info("syncing currriculum data")

        log.info("  loading course data")
        courses: dict[str, CourseDetails] = pydantic.parse_raw_as(
            dict[str, CourseDetails],
            await load_packed(COURSEDATA_PACK_ID),
        )

        log.info("  collating plans")
        storage = await collate_plans(courses)

        log.info("  saving curriculum data to db")
        await _save_packed(CURRICULUMS_PACK_ID, storage.json())

        log.info("  clearing equivalences from db")
        await DbEquivalenceCourse.prisma().delete_many()
        await DbEquivalence.prisma().delete_many()

        log.info("  saving equivalences to db")
        await _store_equivalences_to_db(storage.lists)

        if sync_curriculum:
            # Store new offer to database
            log.info("  syncing curriculum offer")
            await _store_curriculum_offer_to_db(storage)


async def _update_packed_coursedata_in_database():
    """
    Fetch all courses from database, pack them, and store the compacted JSON in the
    database.
    """
    log.info("    loading courses from db")
    all_courses = await DbCourse.prisma().find_many()
    log.info("    packing into json")
    course_dict = (
        f'"{course.code}":{CourseDetails.from_db(course).json()}'
        for course in all_courses
    )
    packed = f"{{{','.join(course_dict)}}}"
    print("    storing to database")
    await _save_packed(COURSEDATA_PACK_ID, packed)


async def _store_equivalences_to_db(lists: dict[str, EquivDetails]):
    for equiv in lists.values():
        # Add equivalence to database
        await DbEquivalence.prisma().create(
            {
                "code": equiv.code,
                "name": equiv.name,
                "is_homogeneous": equiv.is_homogeneous,
                "is_unessential": equiv.is_unessential,
            },
        )
        # Add the courses of the equivalence to database
        value_tuples: list[str] = []
        query_args = [equiv.code]
        for i, code in enumerate(equiv.courses):
            value_tuples.append(
                f"({i}, $1, ${2+i})",
            )  # NOTE: No user-input is injected here
            query_args.append(code)
        if len(value_tuples) == 0:
            raise Exception(f"equivalence {equiv.code} has no courses?")
        await DbEquivalenceCourse.prisma().query_raw(
            f"""
            INSERT INTO "EquivalenceCourse" (index, equiv_code, course_code)
            VALUES {','.join(value_tuples)}
            ON CONFLICT
            DO NOTHING
            """,  # noqa: S608 (only numbers are inserted in string)
            *query_args,
        )


async def _store_curriculum_offer_to_db(storage: CurriculumStorage):
    """
    Take the curriculum offer that is stored in `storage` and store it persistently in
    the database.
    """

    # Delete the previous offer
    await DbMajor.prisma().delete_many()
    await DbMinor.prisma().delete_many()
    await DbTitle.prisma().delete_many()
    await DbMajorMinor.prisma().delete_many()

    # Store major list
    majors: list[MajorCreateInput] = []
    for cyear, offer in storage.offer.items():
        for major in offer.major.values():
            majors.append(
                {
                    "cyear": cyear,
                    "code": major.code,
                    "name": major.name,
                    "version": major.version,  # TODO
                },
            )
    await DbMajor.prisma().create_many(majors)

    # Store minor list
    minors: list[MinorCreateInput] = []
    for cyear, offer in storage.offer.items():
        for minor in offer.minor.values():
            minors.append(
                {
                    "cyear": cyear,
                    "code": minor.code,
                    "name": minor.name,
                    "version": minor.version,
                    "minor_type": minor.program_type,
                },
            )
    await DbMinor.prisma().create_many(minors)

    # Store title list
    titles: list[TitleCreateInput] = []
    for cyear, offer in storage.offer.items():
        for title in offer.title.values():
            titles.append(
                {
                    "cyear": cyear,
                    "code": title.code,
                    "name": title.name,
                    "version": title.version,
                    "title_type": title.program_type,
                },
            )
    await DbTitle.prisma().create_many(titles)

    # Store major-minor associations
    major_minor: list[MajorMinorCreateInput] = []
    for cyear, offer in storage.offer.items():
        for major in offer.major:
            for minor in offer.major_minor[major]:
                major_minor.append(
                    {
                        "cyear": cyear,
                        "major": major,
                        "minor": minor,
                    },
                )
    await DbMajorMinor.prisma().create_many(major_minor)


async def _save_packed(id: str, data: str):
    await DbPackedData.prisma().query_raw(
        """
        INSERT INTO "PackedData" (id, data)
        VALUES ($1, $2)
        ON CONFLICT (id)
        DO UPDATE SET data = $2
        """,
        id,
        data,
    )


class NoPackedDataError(Exception):
    pass


async def load_packed(id: str) -> str:
    packed = await DbPackedData.prisma().find_unique(where={"id": id})
    if packed is None:
        raise NoPackedDataError(
            f"packed data {id} is missing from database"
            " (maybe prestartup script was not run?)",
        )
    return packed.data
