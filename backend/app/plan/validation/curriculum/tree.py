"""
Models a flow network in the context of curriculums.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from ...course import PseudoCourse

SUPERBLOCK_PREFIX = "superblock:"


class FillerCourse(BaseModel):
    """
    Fill a block with a certain course or equivalency.
    If a filler course has to be used, the plan is considered incomplete.
    """

    # The code of the filler course or equivalency.
    course: PseudoCourse
    # Where to place this recommendation relative to other recommendations.
    # The order indicates if the course should be taken early or late in the
    # student's career plan.
    order: int
    # When there is an option on which courses to fill with, this cost determines which
    # course is used.
    # This cost is added with a big number to determine the actual cost of filling with
    # this course.
    cost: int = 0


class BaseBlock(BaseModel):
    # The name of this block.
    # Used for debug purposes.
    debug_name: str
    # Computer-readable code for this block.
    # Identifies the block.
    block_code: str
    # The user-facing name of this block.
    # May not be present (eg. the root block has no name).
    name: str | None
    # What is the maximum amount of credits that this node can support.
    cap: int


class Combination(BaseBlock):
    # Children nodes that supply flow to this block.
    children: list["Block"]


class Leaf(BaseBlock):
    # A set of course codes that comprise this leaf.
    # The value of the dictionary is the maximum amount of repetitions allowed to still
    # count as valid credits.
    # In most cases this should be `1`, but for example equivalences should count
    # unlimited times (`None`), and selecciones deportivas can count twice.
    codes: dict[str, int | None]
    # Indicates courses which will be used to fill the credits for this block if it
    # can't be done with taken courses.
    # If there are more filler courses than missing credits, the list is truncated.
    # Therefore, prefer to place courses with a high `order` number first.
    fill_with: list[FillerCourse] = Field(default_factory=list)
    # Course nodes are deduplicated by their codes.
    # However, this behavior can be controlled by the `layer` property.
    # Course nodes with different `layer` values will not be deduplicated.
    # Useful to model the title exclusive-credit requirements.
    # The default layer is just an empty string.
    layer: str = ""


Block = Combination | Leaf


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
        return Curriculum(
            root=Combination(
                debug_name="Raíz",
                block_code="root",
                name=None,
                cap=0,
                children=[],
            ),
        )


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
    major: str | None
    # Minor code.
    minor: str | None
    # Title code.
    title: str | None
