"""
Models a flow network in the context of curriculums.
"""

from pydantic import BaseModel
from typing import Union


class Combine(BaseModel):
    name: str
    cap: int | None = None
    exclusive: bool | None = None
    children: list["Node"]


Node = Union[Combine, str]


Combine.update_forward_refs()


class Curriculum(BaseModel):
    blocks: list[Combine]
