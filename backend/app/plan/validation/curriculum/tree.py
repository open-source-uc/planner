"""
Models a flow network in the context of curriculums.
"""

from pydantic import BaseModel
from typing import Optional, Union


class Block(BaseModel):
    name: Optional[str] = None
    exclusive: Optional[bool] = None
    cap: Optional[int] = None
    children: list["Node"]


class CourseList(BaseModel):
    name: Optional[str] = None
    cap: int
    codes: list[str]


Node = Union[Block, CourseList, str]


Block.update_forward_refs()


class Curriculum(BaseModel):
    blocks: list[Block]
