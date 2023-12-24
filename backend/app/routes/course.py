from fastapi import APIRouter
from prisma.models import (
    Course as DbCourse,
)
from prisma.types import CourseWhereInput, CourseWhereInputRecursive2
from pydantic import BaseModel
from unidecode import unidecode

from app.plan.courseinfo import (
    CourseDetails,
    EquivDetails,
    course_info,
    make_searchable_name,
)
from app.plan.validation.curriculum.tree import CurriculumSpec
from app.sync import get_curriculum

router = APIRouter(prefix="/course")


class CourseOverview(BaseModel):
    code: str
    name: str
    credits: int
    school: str
    area: str | None
    is_available: bool


class CourseFilter(BaseModel):
    # Only allow courses that match the given search string, in name or course code.
    text: str | None = None
    # Only allow courses that have the given amount of credits.
    credits: int | None = None
    # Only allow courses matching the given school.
    school: str | None = None
    # Only allow courses that match the given availability.
    available: bool | None = None
    # Only allow courses that are available/unavailable on first semesters.
    first_semester: bool | None = None
    # Only allow courses that are available/unavailable on second semesters.
    second_semester: bool | None = None
    # Only allow courses that are members of the given equivalence.
    equiv: str | None = None

    def as_db_filter(self) -> CourseWhereInput:
        filter = CourseWhereInput()
        if self.text is not None:
            search_text = make_searchable_name(self.text)
            name_parts: list[CourseWhereInputRecursive2] = [
                {"searchable_name": {"contains": text_part}}
                for text_part in search_text.split()
            ]
            filter["OR"] = [
                {"code": {"contains": search_text.upper()}},
                {"AND": name_parts},
            ]
        if self.credits is not None:
            filter["credits"] = self.credits
        if self.school is not None:
            ascii_school = unidecode(self.school)
            filter["school"] = {"contains": ascii_school, "mode": "insensitive"}
        if self.available is not None:
            filter["is_available"] = self.available
        if self.first_semester is not None:
            filter["semestrality_first"] = self.first_semester
        if self.second_semester is not None:
            filter["semestrality_second"] = self.second_semester
        if self.equiv is not None:
            filter["equivs"] = {"some": {"equiv_code": self.equiv}}
        return filter


# This should be a GET request, but FastAPI does not support JSON in GET requests
# easily.
# See https://github.com/tiangolo/fastapi/discussions/7919
@router.post("/search/details", response_model=list[CourseOverview])
async def search_course_details(filter: CourseFilter):
    """
    Fetches a list of courses that match the given name (or code),
    credits and school.
    """
    return await DbCourse.prisma().find_many(where=filter.as_db_filter(), take=50)


# This should be a GET request, but FastAPI does not support JSON in GET requests
# easily.
# See https://github.com/tiangolo/fastapi/discussions/7919
@router.post("/search/codes", response_model=list[str])
async def search_course_codes(filter: CourseFilter):
    """
    Fetches a list of courses that match the given name (or code),
    credits and school.
    Returns only the course codes, but allows up to 3000 results.
    """
    return [
        c.code
        for c in await DbCourse.prisma().find_many(
            where=filter.as_db_filter(),
            take=3000,
        )
    ]


# Again, REST-FastAPI is broken. This should be GET, but the parameters are complex so
# it has to be POST.
@router.post("/details", response_model=list[CourseDetails | EquivDetails | None])
async def get_pseudocourse_details(
    codes: list[str],
    plan: CurriculumSpec | None = None,
) -> list[CourseDetails | EquivDetails | None]:
    """
    For a list of course or equivalence codes, fetch a corresponding list of
    course/equivalence details.
    Returns null in the corresponding slot if the code is unknown.

    Additionally, a curriculum spec can be specified. In this case, all equivalences in
    the plan will be fetched and appended to the list.
    """

    if plan is not None:
        curriculum = await get_curriculum(plan)
        codes.extend(curriculum.collect_equivalences())

    courseinfo = await course_info()
    courses: list[CourseDetails | EquivDetails | None] = [
        courseinfo.try_course(code) or courseinfo.try_equiv(code) for code in codes
    ]

    return courses
