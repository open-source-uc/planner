from .validation.curriculum.tree import CurriculumSpec
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
    An academic plan submitted by a user.
    Contains all of the courses they have passed and intend to pass.
    Also contains all of the context associated with the user (e.g. their choice of
    major and minor).

    Including user context here allows plans to be validated without external context,
    allowing guests to simulate any plans they want to try out.
    """

    # NOTE: Modifying this class breaks all the JSON stored in the DB
    # Currently, we don't handle migrations at all.
    # Eventually, we will have to roll our own migration system if we allow
    # ValidatablePlans to be exportable/importable.

    # TODO: Warn when the real user context does not match the context in
    # `ValidatablePlan`.
    # For example, when exporting/importing is implemented, a user with `C2020` could
    # import a plan made by a `C2021` user, and the context would not match.
    # In this case, the correct approach is to warn the user that the plan was made for
    # `C2021`, and to automatically correct the context.

    # Classes per semester.
    classes: list[list[PseudoCourse]]
    # The first semester to validate.
    # Semesters before this semester are considered approved.
    next_semester: int
    # Academic level of the student
    level: Optional[Level]
    # Academic school (facultad) of the student
    school: Optional[str]
    # Academic program of the student (magisteres, doctorados, etc)
    program: Optional[str]
    # Career of the student
    career: Optional[str]
    # The curriculum that the user wants to pursue
    # Validate the plan against this curriculum
    curriculum: CurriculumSpec


class ClassIndex(BaseModel, frozen=True):
    """
    An index of a course instance within a validatable plan.
    """

    # The semester where the course is located.
    semester: int
    # The index of the course within the semester.
    position: int
