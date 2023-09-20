"""
Models a flow network in the context of curriculums.
"""

import re
from collections.abc import Callable, Generator
from typing import Annotated, Any, Literal, Optional, Self

from pydantic import BaseModel, Field
from pydantic.fields import ModelField

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
    # Computer-readable code for this block.
    # Identifies the block.
    block_code: str
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

    # A set of course codes that comprise this leaf.
    # This should include the equivalence code!
    codes: set[str]
    # Course nodes are deduplicated by their codes.
    # However, this behavior can be controlled by the `layer` property.
    # Course nodes with different `layer` values will not be deduplicated.
    # Useful to model the minor and title exclusive-credit requirements.
    # The default layer is just an empty string.
    layer: str = ""


Block = Combination | Leaf


Combination.update_forward_refs()


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
        infinite (eg. multiplicity["!L1"] = `None`).

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
                block_code="root",
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


class Cyear(BaseModel, frozen=True):
    """
    A curriculum version, constrained to whatever curriculum versions we support.
    Whenever something depends on the version of the curriculum, it should match
    exhaustively on the `raw` field (using Python's `match` statement).
    This allows the linter to pinpoint all places that need to be updated whenever a
    new curriculum version is added.

    NOTE: Remember to reset the cache in the database after any changes, either manually
    or through migrations.
    """

    raw: Literal["C2020"] | Literal["C2022"]

    @staticmethod
    def from_str(cyear: str) -> Optional["Cyear"]:
        if cyear == "C2020" or cyear == "C2022":
            return Cyear(raw=cyear)
        return None

    def __str__(self) -> str:
        """
        Intended for communication with untyped systems like SIDING or the database.
        To switch based on the curriculum version, use `raw` directly, which
        preserves type information.
        """
        return self.raw


LATEST_CYEAR = Cyear(raw="C2022")


class CurriculumCode(str):
    """
    A code for a major or a minor.
    """

    _pattern: re.Pattern[str]

    def __new__(cls: type[Self], value: str) -> Self:
        return super().__new__(cls, value)

    @classmethod
    def __get_validators__(
        cls: type[Self],
    ) -> Generator[Callable[..., Self], None, None]:
        yield cls.validate

    @classmethod
    def validate(cls: type[Self], value: str, field: ModelField) -> Self:
        assert cls._pattern is not None
        if not isinstance(value, str):  # type: ignore
            raise TypeError("string required")
        value = value.strip().upper()
        m = cls._pattern.fullmatch(value)
        if m is None:
            raise ValueError(f"Invalid {cls.__name__} code {value}")
        return cls(value)

    @classmethod
    def __modify_schema__(cls: type[Self], field_schema: dict[str, Any]) -> None:
        raise NotImplementedError


class MajorCode(CurriculumCode):
    _pattern = re.compile(r"^M[0-9]{3}$")

    @classmethod
    def __modify_schema__(cls: type[Self], field_schema: dict[str, Any]) -> None:
        field_schema.update(
            description="A major code, eg. `M072` for hydraulic engineering.",
            pattern=cls._pattern.pattern,
            examples=["M072", "M262", "M232"],
        )


class MinorCode(CurriculumCode):
    _pattern = re.compile(r"^N[0-9]{3}$")

    @classmethod
    def __modify_schema__(cls: type[Self], field_schema: dict[str, Any]) -> None:
        field_schema.update(
            description="A minor code, eg. `N204` for numerical analysis.",
            pattern=cls._pattern.pattern,
            examples=["N204", "N199", "N776"],
        )


class TitleCode(CurriculumCode):
    _pattern = re.compile(r"^4[0-9]{4}(?:-[0-9])?$")

    @classmethod
    def __modify_schema__(cls: type[Self], field_schema: dict[str, Any]) -> None:
        field_schema.update(
            description="A title code, eg. `40007` for a computer engineering.",
            pattern=cls._pattern.pattern,
            examples=["40008", "40023", "40096"],
        )


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
        return self.copy(update={"major": major})

    def with_minor(self, minor: MinorCode | None) -> "CurriculumSpec":
        return self.copy(update={"minor": minor})

    def with_title(self, title: TitleCode | None) -> "CurriculumSpec":
        return self.copy(update={"title": title})

    def no_major(self) -> "CurriculumSpec":
        return self.with_major(None)

    def no_minor(self) -> "CurriculumSpec":
        return self.with_minor(None)

    def no_title(self) -> "CurriculumSpec":
        return self.with_title(None)
