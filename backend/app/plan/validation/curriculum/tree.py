"""
Models a flow network in the context of curriculums.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.plan.course import PseudoCourse
from app.plan.courseinfo import CourseInfo

SUPERBLOCK_PREFIX = "superblock:"


class FillerCourse(BaseModel):
    """
    Fill a block with a certain course or equivalency.
    If a filler course has to be used, the plan is considered incomplete.

    NOTE: Remember to reset the cache in the database after any changes, either manually
    or through migrations.
    """

    # The code of the filler course or equivalency.
    course: PseudoCourse
    # Where to place this recommendation relative to other recommendations.
    # The order indicates if the course should be taken early or late in the
    # student's career plan.
    order: int
    # Additive cost of using this filler course.
    cost_offset: int = 0


class BaseBlock(BaseModel):
    """
    NOTE: Remember to reset the cache in the database after any changes, either manually
    or through migrations.
    """

    # The name of this block.
    # Used for debug purposes.
    debug_name: str
    # The user-facing name of this block.
    # May not be present (eg. the root block has no name).
    name: str | None
    # What is the maximum amount of credits that this node can support.
    cap: int

    def __hash__(self) -> int:
        return id(self) // 16

    def __eq__(self, rhs: "BaseBlock") -> bool:
        return id(self) == id(rhs)


class Combination(BaseBlock):
    """
    NOTE: Remember to reset the cache in the database after any changes, either manually
    or through migrations.
    """

    # Children nodes that supply flow to this block.
    children: list["Block"]

    def freeze_capacities(self):
        """
        If this node or any of its descendants have -1 capacity, replace these invalid
        capacities by the total capacity of their children.
        """

        for child in self.children:
            if isinstance(child, Combination):
                child.freeze_capacities()
        if self.cap == -1:
            self.cap = sum(child.cap for child in self.children)


class Leaf(BaseBlock):
    """
    NOTE: Remember to reset the cache in the database after any changes, either manually
    or through migrations.
    """

    # The list code that identifies this leaf.
    # Note that this ID might not be unique.
    # For example, C2020 OFGs all share the same list code, but there are extra rules
    # that are modeled using several leaves.
    list_code: str
    # A set of course codes that comprise this leaf.
    # This should include the equivalence code!
    codes: set[str]
    # The ID of the superblock that this course belongs to.
    superblock: str
    # Course nodes are deduplicated by their codes.
    # However, this behavior can be controlled by the `layer` property.
    # Course nodes with different `layer` values will not be deduplicated.
    # Useful to model the minor and title exclusive-credit requirements.
    # The default layer is just an empty string.
    layer: str = ""


Block = Combination | Leaf


Combination.model_rebuild()


class Multiplicity(BaseModel):
    group: set[str]
    credits: int | None


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
        infinite (eg. multiplicity["MAJOR-L1"] = `None`).

        Additionally, multiplicity specifies which courses should be equivalent in terms
        of credit count.
        For example, if TTF010 has a multiplicity group of [TTF010, TEO200] then taking
        TTF010 or TEO200 is exactly the same, and the multiplicity is compared against
        the total of credits among both courses.

    NOTE: Remember to reset the cache in the database after any changes, either manually
    or through migrations.
    """

    root: Combination
    fillers: dict[str, list[FillerCourse]]
    multiplicity: dict[str, Multiplicity]

    @staticmethod
    def empty() -> "Curriculum":
        return Curriculum(
            root=Combination(
                debug_name="Raíz",
                name=None,
                cap=0,
                children=[],
            ),
            fillers={},
            multiplicity={},
        )

    def extend(self, other: "Curriculum"):
        self.root.children.extend(other.root.children)
        self.root.cap += other.root.cap
        for code, fillers in other.fillers.items():
            self.fillers.setdefault(code, []).extend(fillers)
        self.multiplicity.update(other.multiplicity)

    def multiplicity_of(self, courseinfo: CourseInfo, course_code: str) -> Multiplicity:
        if course_code in self.multiplicity:
            return self.multiplicity[course_code]
        info = courseinfo.try_course(course_code)
        if info is not None:
            return Multiplicity(group={course_code}, credits=info.credits or 1)
        # TODO: Limit equivalence multiplicity to the total amount of credits in the
        # equivalence.
        # Ideally, we would want to store the total amount of credits in a field in the
        # equivalence, otherwise it is probably too costly to visit the 2000+ course
        # OFG equivalence.
        return Multiplicity(group={course_code}, credits=None)


# A curriculum version, constrained to whatever curriculum versions we support.
# Whenever any code depends on the version of the curriculum, it should use `match`
# blocks to exhaustively match on the versions.
# This way, when a new version is added the linter can spot all of the locations where
# the code depends on `Cyear`.
Cyear = Literal["C2020"] | Literal["C2022"]


def cyear_from_str(cyear: str) -> Cyear | None:
    match cyear:
        case "C2020" | "C2022":
            return cyear
        case _:
            return None


LATEST_CYEAR: Cyear = "C2022"


MajorCode = Annotated[str, StringConstraints(pattern=r"^M[0-9]{3}$")]
MinorCode = Annotated[str, StringConstraints(pattern=r"^N[0-9]{3}$")]
TitleCode = Annotated[str, StringConstraints(pattern=r"^4[0-9]{4}(?:-[0-9])?$")]


class CurriculumSpec(BaseModel, frozen=True):
    """
    Represents a curriculum specification.
    This specification should uniquely identify a curriculum, although it contains no
    information about the curriculum itself.

    NOTE: Remember to reset the cache in the database after any changes, either manually
    or through migrations.
    """

    cyear: Annotated[Cyear, Field(description="The curriculum version.")]
    major: MajorCode | None
    minor: MinorCode | None
    title: TitleCode | None

    def has_major(self) -> bool:
        return self.major is not None

    def has_minor(self) -> bool:
        return self.minor is not None

    def has_title(self) -> bool:
        return self.title is not None

    def with_major(self, major: MajorCode | None) -> "CurriculumSpec":
        return self.model_copy(update={"major": major})

    def with_minor(self, minor: MinorCode | None) -> "CurriculumSpec":
        return self.model_copy(update={"minor": minor})

    def with_title(self, title: TitleCode | None) -> "CurriculumSpec":
        return self.model_copy(update={"title": title})

    def no_major(self) -> "CurriculumSpec":
        return self.with_major(None)

    def no_minor(self) -> "CurriculumSpec":
        return self.with_minor(None)

    def no_title(self) -> "CurriculumSpec":
        return self.with_title(None)

    def __str__(self) -> str:
        s = self.cyear
        if self.major is not None:
            s += f"-{self.major}"
        if self.minor is not None:
            s += f"-{self.minor}"
        if self.title is not None:
            s += f"-{self.title}"
        return s
