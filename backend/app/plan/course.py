from typing import Annotated, Literal

from pydantic import BaseModel, Field


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
    equivalence: EquivalenceId | None
    # If this course is a failed course, what course was failed.
    failed: str | None = None


PseudoCourse = Annotated[
    ConcreteId | EquivalenceId,
    Field(discriminator="is_concrete"),
]


def pseudocourse_with_credits(pseudocourse: PseudoCourse, credits: int) -> PseudoCourse:
    """
    Create a copy of the given pseudocourse but with a certain amount of credits.
    Does a best-effort attempt. If the course is concrete then only the credits of the
    associated equivalence can be modified.
    """
    if isinstance(pseudocourse, EquivalenceId):
        if pseudocourse.credits != credits:
            return EquivalenceId(code=pseudocourse.code, credits=credits)
    elif pseudocourse.equivalence is not None:
        return ConcreteId(
            code=pseudocourse.code,
            failed=pseudocourse.failed,
            equivalence=EquivalenceId(
                code=pseudocourse.equivalence.code,
                credits=credits,
            ),
        )
    return pseudocourse
