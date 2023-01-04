"""
Models a flow network in the context of curriculums.
"""

from pydantic import BaseModel
from typing import Optional, Union


class BaseNode(BaseModel):
    name: Optional[str] = None
    exclusive: Optional[bool] = None


class InternalNode(BaseNode):
    children: list["Node"]


class Block(InternalNode):
    name: str


class RequireSome(InternalNode):
    capacity: int


class CourseList(BaseNode):
    courses: list[str]


Node = Union[Block, RequireSome, CourseList, str]


Block.update_forward_refs()
RequireSome.update_forward_refs()


class Curriculum(BaseModel):
    blocks: list[Block]
