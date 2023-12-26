from app.plan.courseinfo import CourseInfo
from app.plan.validation.curriculum.tree import (
    CurriculumSpec,
)
from app.sync.curriculums.scrape.minor import ScrapedProgram
from app.sync.curriculums.scrape.translate import ProgramType, translate_scrape
from app.sync.curriculums.siding import SidingInfo
from app.sync.curriculums.storage import CurriculumStorage, ProgramDetails
from app.sync.siding.client import BloqueMalla

MINOR_TYPE = ProgramType(
    superblock_id="Minor",
    readable_id="Minor",
    layer_id="minor",
    order_base=100,
    exclusive_credits=None,
)


def translate_minor(
    courseinfo: CourseInfo,
    out: CurriculumStorage,
    spec: CurriculumSpec,
    meta: ProgramDetails,
    siding_info: SidingInfo,
    siding: list[BloqueMalla],
    scrape: ScrapedProgram,
):
    curr = translate_scrape(
        MINOR_TYPE,
        courseinfo,
        out,
        spec,
        meta.name,
        siding_info,
        siding,
        scrape,
    )

    out.set_minor(spec, curr)
