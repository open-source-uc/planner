"""
Models a flow network in the context of curriculums.
"""

from typing import Literal, Optional

from pydantic import BaseModel

from ...course import PseudoCourse
from ...courseinfo import CourseInfo

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
    # This should include the equivalence code!
    codes: set[str]
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

    - root: The root of the curriculum tree.
    - mutiplicity: Specifies the multiplicity of each course, in credits.
        Multiplicity limits the amount of times a course can be repeated.
        For example, if course TTF010 has a multiplicity of 15 credits, and the course
        TTF010 is worth 10 credits, then taking the TTF010 course twice only accounts to
        15 total credits.
        If a course has no multiplicity, then it defaults to the amount of credits of
        the course (eg. the TTF010 example above would have a 10-credit multiplicity).
        This makes it so that by default each course only counts at most once.
        For equivalencies that have no associated credit count, the multiplicity is
        infinite (eg. multiplicity["!L1"] = `None`).
    - equivalencies: Specifies a course as being equivalent to another course. All
        courses in an equivalence must point to the same course code.
        (eg. FIS1523 -> FIS1523, IEE1523 -> FIS1523).
        If not present for a particular course, it defaults to being equivalent with
        itself.
    """

    root: Combination
    fillers: dict[str, list[FillerCourse]]
    multiplicity: dict[str, int | None]
    equivalencies: dict[str, str]

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
            fillers={},
            multiplicity={},
            equivalencies={},
        )

    def extend(self, other: "Curriculum"):
        self.root.children.extend(other.root.children)
        self.root.cap += other.root.cap
        for code, fillers in other.fillers.items():
            self.fillers.setdefault(code, []).extend(fillers)
        self.multiplicity.update(other.multiplicity)
        self.equivalencies.update(other.equivalencies)

    def multiplicity_of(self, courseinfo: CourseInfo, course_code: str) -> int | None:
        if course_code in self.multiplicity:
            return self.multiplicity[course_code]
        info = courseinfo.try_course(course_code)
        if info is not None:
            return info.credits or 1
        # TODO: Limit equivalence multiplicity to the total amount of credits in the
        # equivalence.
        # Ideally, we would want to store the total amount of credits in a field in the
        # equivalence, otherwise it is probably too costly to visit the 2000+ course
        # OFG equivalence.
        return None


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
