from pydantic import BaseModel
from typing import Optional
from enum import Enum


class Level(int, Enum):
    """
    An academic level.
    """

    # TODO: Confirm this order, is it correct?
    PREGRADO = 1
    POSTITULO = 2
    MAGISTER = 3
    DOCTORADO = 4


class ValidatablePlan(BaseModel):
    """
    Raw plan submitted by a user.
    Also contains context about the user.
    `ValidatablePlan` should represent any user & plan configuration.
    """

    # NOTE: remember to migrate JSON in DB when modifying this class

    # Classes per semester.
    classes: list[list[str]]
    # The first semester to validate.
    # Semester before this semester are considered approved.
    next_semester: int
    # Academic level of the student
    level: Optional[Level] = None
    # Academic school (facultad) of the student
    school: Optional[str] = None
    # Academic program of the student (magisteres, doctorados, etc)
    program: Optional[str] = None
    # Career of the student
    career: Optional[str] = None
