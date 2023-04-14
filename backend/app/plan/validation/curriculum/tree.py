"""
Models a flow network in the context of curriculums.
"""

from pydantic import BaseModel
from typing import ClassVar, Literal, Optional, Union


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


class CurriculumSpec(BaseModel, frozen=True):
    """
    Represents a curriculum specification.
    This specification should uniquely specify a curriculum.
    """

    LATEST_CYEAR: ClassVar[Literal["C2020"]] = "C2020"

    # Curriculum year.
    cyear: Literal["C2020"]
    # Major code.
    major: Optional[str]
    # Minor code.
    minor: Optional[str]
    # Title code.
    title: Optional[str]
