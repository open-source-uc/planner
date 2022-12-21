"""
Models a flow network in the context of curriculums.
"""

from pydantic import BaseModel
from typing import Optional, Union


class Combine(BaseModel):
    name: str
    # Maximum flow that the node can receive before becoming saturated.
    # Defaults to the sum of its children.
    cap: Optional[int] = None
    # Defines whether course dependencies should be exclusive or not.
    # If `None`, the node inherits its exclusiveness from its parent.
    exclusive: Optional[bool] = None
    # List of children nodes that can supply flow to this node.
    children: list["Node"]


Node = Union[Combine, str]


Combine.update_forward_refs()


class Curriculum(BaseModel):
    blocks: list[Combine]
