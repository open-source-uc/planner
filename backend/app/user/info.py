"""
Definitions of basic student information.
"""


from typing import Optional
from ..plan.plan import PseudoCourse
from pydantic import BaseModel


class StudentInfo(BaseModel):
    # Full name, all uppercase, with Unicode accents.
    full_name: str
    # Curriculum version that applies to this user.
    # Note that this is represented as a `str` rather than a `Cyear`.
    # This means that the user's curriculum may potentially not be supported!
    cyear: str
    # Whether the curriculum version has a matching supported version or not.
    is_cyear_supported: bool
    # The year and semester of admission.
    # E.g `(2021, 1)` for the first semester of the year 2021
    admission: tuple[int, int]
    # The self-reported major code.
    reported_major: Optional[str]
    # The self-reported minor code.
    reported_minor: Optional[str]
    # The self-reported title code.
    reported_title: Optional[str]


class StudentContext(BaseModel):
    info: StudentInfo
    passed_courses: list[list[PseudoCourse]]
