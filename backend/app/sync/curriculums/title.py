from app.plan.courseinfo import CourseInfo
from app.plan.validation.curriculum.tree import CurriculumSpec
from app.sync.curriculums.scrape.title import ScrapedTitle
from app.sync.curriculums.storage import CurriculumStorage
from app.sync.siding.client import BloqueMalla


def translate_title(
    courseinfo: CourseInfo,
    out: CurriculumStorage,
    spec: CurriculumSpec,
    siding: list[BloqueMalla],
    scrape: ScrapedTitle,
):
    # TODO: Translate titles
    pass
