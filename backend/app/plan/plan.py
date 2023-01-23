from pydantic import BaseModel, Field
from typing import Annotated, Literal, Optional, Union
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


class EquivalenceId(BaseModel, frozen=True):
    is_concrete: Literal[False] = False
    # The internal code of this abstract equivalence.
    # This code is associated with a list of courses that are equivalent under the
    # scope of this equivalence.
    #
    # NOTE: Equivalence codes and concrete course codes share the same namespace.
    # This means that all equivalence codes are different from all course codes.
    # (Because equivalence codes are always prefixed by a `?`)
    code: str
    # How many credits worth of this equivalence does this pseudocourse stand for.
    credits: int


class ConcreteId(BaseModel, frozen=True):
    is_concrete: Literal[True] = True
    # The unique course code representing this course.
    code: str
    # If this course belongs to an equivalence, this field indicates it.
    equivalence: Optional[EquivalenceId] = None


PseudoCourse = Annotated[
    Union[ConcreteId, EquivalenceId], Field(discriminator="is_concrete")
]


class ValidatablePlan(BaseModel):
    """
    Raw plan submitted by a user.
    Also contains context about the user.
    `ValidatablePlan` should represent any user & plan configuration.
    """

    # NOTE: remember to migrate JSON in DB when modifying this class

    # Classes per semester.
    classes: list[list[PseudoCourse]]
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
