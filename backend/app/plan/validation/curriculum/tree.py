"""
Models a flow network in the context of curriculums.
"""

from pydantic import BaseModel
from typing import Literal, Optional, Union


class Block(BaseModel):
    superblock: str
    name: Optional[str] = None
    exclusive: Optional[bool] = None
    cap: Optional[int] = None
    children: list["Node"]


class CourseList(BaseModel):
    # The academic block that this course list belongs to.
    superblock: str
    # The human-readable name of this course list.
    name: Optional[str] = None
    # The amount of credits that this course list expects to be filled with.
    cap: int
    # The machine code for this course list.
    # The "id" of this course list.
    equivalence_code: Optional[str]
    # List of concrete courses that fulfill this equivalence.
    codes: list[str]
    # TODO: Give this value meaning.
    # In order to do this, first we have to figure out how Seguimiento Curricular
    # actually works.
    priority: int


Node = Union[Block, CourseList]


Block.update_forward_refs()


class Curriculum(BaseModel):
    nodes: list[Node]


class Cyear(BaseModel, frozen=True):
    """
    A curriculum version, constrained to whatever curriculum versions we support.
    Whenever something depends on the version of the curriculum, it should match
    exhaustively on the `raw` field (using Python's `match` statement).
    This allows the linter to pinpoint all places that need to be updated whenever a
    new curriculum version is added.
    """

    raw: Literal["C2020"]

    @staticmethod
    def from_str(cyear: str) -> Optional["Cyear"]:
        if cyear == "C2020":
            return Cyear(raw=cyear)
        else:
            return None

    def __str__(self) -> str:
        """
        Intended for communication with untyped systems like SIDING or the database.
        To switch based on the curriculum version, use `raw` directly, which
        preserves type information.
        """
        return self.raw


LATEST_CYEAR = Cyear(raw="C2020")


class CurriculumSpec(BaseModel, frozen=True):
    """
    Represents a curriculum specification.
    This specification should uniquely specify a curriculum.
    """

    # Curriculum year.
    cyear: Cyear
    # Major code.
    major: Optional[str]
    # Minor code.
    minor: Optional[str]
    # Title code.
    title: Optional[str]
