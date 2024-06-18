"""
Definitions of basic student information.
"""

from pydantic import BaseModel

from app.plan.course import PseudoCourse
from app.plan.validation.curriculum.tree import MajorCode, MinorCode, TitleCode


class StudentInfo(BaseModel):
    # Full name, all uppercase, with Unicode accents.
    full_name: str

    # Curriculum version that applies to this user.
    # Note that this is represented as a `str` rather than a `Cyear`.
    # This means that the user's curriculum may potentially not be supported!
    cyear: str
    # Whether the curriculum version has a matching supported version or not.
    is_cyear_supported: bool

    # The self-reported major code.
    reported_major: MajorCode | None
    # The self-reported minor code.
    reported_minor: MinorCode | None
    # The self-reported title code.
    reported_title: TitleCode | None

    # The student's taken courses up to now.
    passed_courses: list[list[PseudoCourse]]
    # The index of the current semester (or the next semester if currently in between
    # semesters).
    current_semester: int
    # The index of the next semester (ie. if the student is currently coursing a
    # semester, it points to the semester after this one).
    # This is the index of the first semester where courses have not yet been taken.
    # (This property is useful because we do not want to generate errors for semesters
    # where their courses have already been taken)
    next_semester: int

    # The period that corresponds to the first semester of the student.
    # A (year, semester) tuple, or `None` if there is no information.
    admission: tuple[int, int] | None
