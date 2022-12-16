"""
Models a flow network in the context of curriculums.
"""

from pydantic import BaseModel, Field
from typing import Annotated, Any, Optional, Union
from hashlib import blake2b as good_hash


# TODO: Model title exclusivity (ie. 130 credits must be "en el titulo")
class Combine(BaseModel):
    name: str
    cap: Optional[int] = None
    children: list["Node"]
    hash_cache: Annotated[bytes, Field(exclude=True)] = bytes()

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

        # Precalculate hash
        h = good_hash(b"comb")
        if self.name is None:
            h.update(b"-")
        else:
            h.update(b"+")
            h.update(self.name.encode("UTF-8"))
        if self.cap is None:
            h.update(b"-")
        else:
            h.update(b"+")
            h.update(self.cap.to_bytes(4))
        for child in self.children:
            h.update(hash_node(child))
        self.hash_cache = h.digest()


Node = Union[Combine, str]


class Curriculum(BaseModel):
    blocks: list[Combine]


def hash_node(node: Node) -> bytes:
    if isinstance(node, str):
        return good_hash(node.encode("UTF-8")).digest()
    return node.hash_cache
