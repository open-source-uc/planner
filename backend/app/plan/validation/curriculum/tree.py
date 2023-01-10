"""
Models a flow network in the context of curriculums.
"""

from pydantic import BaseModel
from typing import Literal, Optional, Union


class Block(BaseModel):
    name: Optional[str] = None
    exclusive: Optional[bool] = None
    cap: Optional[int] = None
    children: list["Node"]


class CourseList(BaseModel):
    name: Optional[str] = None
    cap: int
    codes: list[str]
    priority: int


Node = Union[Block, CourseList]


Block.update_forward_refs()


class Curriculum(BaseModel):
    blocks: list[Block]


class CurriculumSpec(BaseModel):
    """
    Represents a curriculum specification.
    This specification should uniquely specify a curriculum.
    """
    # Curriculum year.
    cyear: Literal["C2020"]
    # Major code.
    major: Optional[str]
    # Minor code.
    minor: Optional[str]
    # Title code.
    title: Optional[str]
