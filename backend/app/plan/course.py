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
    equivalence: EquivalenceId | None = None


PseudoCourse = Annotated[
    ConcreteId | EquivalenceId,
    Field(discriminator="is_concrete"),
]


def pseudocourse_with_credits(pseudocourse: PseudoCourse, credits: int) -> PseudoCourse:
    """
    Attempt to create a copy of this equivalence, but with the given amount of credits.
    """
    return (
        pseudocourse.copy(update={"credits": credits})
        if isinstance(pseudocourse, EquivalenceId)
        else pseudocourse
    )
