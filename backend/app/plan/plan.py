from typing import Literal, Self

from pydantic import (
    BaseModel,
    validator,  # type: ignore
)

from app.plan.course import PseudoCourse
from app.plan.validation.curriculum.tree import CurriculumSpec

CURRENT_PLAN_VERSION = "0.0.2"
MAX_SEMESTERS = 20
MAX_CLASSES = 200


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

    # The version of the plan.
    # We will probably use this if we move to a `StorablePlan`/`ValidatablePlan` divide.
    version: Literal["0.0.2"]
    # Classes per semester.
    classes: list[list[PseudoCourse]]
    # Academic level of the student
    level: str | None
    # Academic school (facultad) of the student
    school: str | None
    # Academic program of the student (magisteres, doctorados, etc)
    program: str | None
    # Career of the student
    career: str | None
    # The curriculum that the user wants to pursue
    # Validate the plan against this curriculum
    curriculum: CurriculumSpec

    @validator("classes")  # type: ignore
    @classmethod
    def validate_limits(
        cls: type[Self],
        classes: list[list[PseudoCourse]],
    ) -> list[list[PseudoCourse]]:
        if len(classes) > MAX_SEMESTERS:
            raise ValueError("too many semesters")
        if sum(len(sem) for sem in classes) > MAX_CLASSES:
            raise ValueError("too many classes")
        return classes


class ClassId(BaseModel, frozen=True):
    """
    A somewhat stable identifier for a course instance within a plan.
    """

    # The code of the course of this class.
    code: str
    # The index of the instance of this course.
    instance: int
