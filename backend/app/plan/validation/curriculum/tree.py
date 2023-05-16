"""
Models a flow network in the context of curriculums.
"""

from ...course import PseudoCourse
from pydantic import BaseModel
from typing import Literal, Optional, Union


class BaseBlock(BaseModel):
    # The name of this block.
    # If this block is missing credits, this name will be used to report.
    name: Optional[str] = None
    # What is the maximum amount of credits that this node can support.
    cap: int
    # If missing credits for this block, fill with the given courses.
    # Contains a priority (lower is sooner) and a course.
    # Courses should be sorted from latest to soonest (from high priority number to low
    # priority number).
    #
    # NOTE: There should be exactly 1 node with a `fill_with` attribute in every path
    # from root to leaf.
    # If this is not respected, some arbitrary node in the path will be chosen.
    fill_with: list[tuple[int, PseudoCourse]] = []


class Combination(BaseBlock):
    # Children nodes that supply flow to this block.
    children: list["Block"]


class Leaf(BaseBlock):
    # A set of course codes that comprise this leaf.
    # The value of the dictionary is the maximum amount of repetitions allowed to still
    # count as valid credits.
    # In most cases this should be `1`, but for example equivalences should count
    # unlimited times (`None`), and selecciones deportivas can count twice.
    codes: dict[str, Optional[int]]
    # Course nodes are deduplicated by their codes.
    # However, this behavior can be controlled by the `layer` property.
    # Course nodes with different `layer` values will not be deduplicated.
    # Useful to model the title exclusive-credit requirements.
    # The default layer is just an empty string.
    layer: str = ""


Block = Union[Combination, Leaf]


Combination.update_forward_refs()


class Curriculum(BaseModel):
    """
    A specific curriculum definition, not associated to any particular student.
    This class could be represented as a graph, but it would have *a lot* of nodes (at
    least one for every possible course in the curriculum definition).
    Instead, we store a representation of the curriculum that is optimized for quickly
    building a graph for a particular (curriculum, user) pair.
    """

    root: Combination

    @staticmethod
    def empty() -> "Curriculum":
        return Curriculum(root=Combination(cap=0, children=[]))


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
    This specification should uniquely identify a curriculum, although it contains no
    information about the curriculum itself.
    """

    # Curriculum year.
    cyear: Cyear
    # Major code.
    major: Optional[str]
    # Minor code.
    minor: Optional[str]
    # Title code.
    title: Optional[str]
