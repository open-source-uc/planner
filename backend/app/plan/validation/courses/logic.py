"""
Implements logical expressions in the context of course requirements.
"""


from abc import abstractmethod
from collections.abc import Callable
from functools import cached_property
from hashlib import blake2b as good_hash
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, Field


class BaseExpr(BaseModel, frozen=True, keep_untouched=(cached_property,)):
    """
    A logical expression.
    The requirements that a student must uphold in order to take a course is expressed
    through a combination of expressions.
    """

    @abstractmethod
    def __str__(self) -> str:
        pass

    @cached_property
    @abstractmethod
    def hash(self) -> Annotated[bytes, Field(exclude=True)]:
        pass


class BaseOp(BaseExpr, frozen=True):
    """
    A logical connector between expressions.
    May be AND or OR.
    """

    neutral: ClassVar[bool]
    children: tuple["Expr", ...]

    def __str__(self) -> str:
        op = "y" if self.neutral else "o"
        s = ""
        for child in self.children:
            if s != "":
                s += f" {op} "
            if isinstance(child, BaseOp):
                s += f"({child})"
            else:
                s += str(child)
        return s

    @cached_property
    def hash(self) -> bytes:
        h = good_hash(b"y" if self.neutral else b"o")
        for child in self.children:
            h.update(child.hash)
        return h.digest()

    @staticmethod
    def create(neutral: bool, children: tuple["Expr", ...]) -> "Operator":
        """
        Build an AND node or an OR node in a generic way, using the neutral element to
        distinguish between them.
        In other words, if `neutral` is true, build an AND node, otherwise build an OR
        node.
        """
        return And(children=children) if neutral else Or(children=children)


class And(BaseOp, frozen=True):
    """
    Logical AND connector.
    Only satisfied if all of its children are satisfied.
    """

    expr: Literal["and"] = Field(default="and", const=True)
    neutral: ClassVar[bool] = True


class Or(BaseOp, frozen=True):
    """
    Logical OR connector.
    Only satisfied if at least one of its children is satisfied.
    """

    expr: Literal["or"] = Field(default="or", const=True)
    neutral: ClassVar[bool] = False


class Const(BaseExpr, frozen=True):
    """
    A constant, fixed value of True or False.
    """

    expr: Literal["const"] = Field(default="const", const=True)
    value: bool

    def __str__(self) -> str:
        return str(self.value)

    @cached_property
    def hash(self) -> bytes:
        h = good_hash(b"one" if self.value else b"zero")
        return h.digest()


class MinCredits(BaseExpr, frozen=True):
    """
    A restriction that is only satisfied if the total amount of credits in the previous
    semesters is over a certain threshold.
    """

    expr: Literal["cred"] = Field(default="cred", const=True)

    min_credits: int

    def __str__(self) -> str:
        return f"(Creditos >= {self.min_credits})"

    @cached_property
    def hash(self) -> bytes:
        h = good_hash(b"cred")
        h.update(self.min_credits.to_bytes(4))
        return h.digest()


class ReqLevel(BaseExpr, frozen=True):
    """
    Express that this course requires a certain academic level.
    """

    expr: Literal["lvl"] = Field(default="lvl", const=True)

    # Takes the values: "Pregrado", "Postitulo", "Magister", "Doctorado".
    level: str

    # Require equality or inequality?
    equal: bool

    def __str__(self) -> str:
        eq = "=" if self.equal else "!="
        return f"(Nivel {eq} {self.level})"

    @cached_property
    def hash(self) -> bytes:
        h = good_hash(b"level")
        h.update(self.level.encode("UTF-8"))
        h.update(b"==" if self.equal else b"!=")
        return h.digest()


class ReqSchool(BaseExpr, frozen=True):
    """
    Express that this course requires the student to belong to a particular school.
    """

    expr: Literal["school"] = Field(default="school", const=True)

    school: str

    # Require equality or inequality?
    equal: bool

    def __str__(self) -> str:
        eq = "=" if self.equal else "!="
        return f"(Facultad {eq} {self.school})"

    @cached_property
    def hash(self) -> bytes:
        h = good_hash(b"school")
        h.update(self.school.encode("UTF-8"))
        h.update(b"==" if self.equal else b"!=")
        return h.digest()


class ReqProgram(BaseExpr, frozen=True):
    """
    Express that this course requires the student to belong to a particular program.
    """

    expr: Literal["program"] = Field(default="program", const=True)

    program: str

    # Require equality or inequality?
    equal: bool

    def __str__(self) -> str:
        eq = "=" if self.equal else "!="
        return f"(Programa {eq} {self.program})"

    @cached_property
    def hash(self) -> bytes:
        h = good_hash(b"program")
        h.update(self.program.encode("UTF-8"))
        h.update(b"==" if self.equal else b"!=")
        return h.digest()


class ReqCareer(BaseExpr, frozen=True):
    """
    Express that this course requires the student to belong to a particular career.
    """

    expr: Literal["career"] = Field(default="career", const=True)

    career: str

    # Require equality or inequality?
    equal: bool

    def __str__(self) -> str:
        eq = "=" if self.equal else "!="
        return f"(Carrera {eq} {self.career})"

    @cached_property
    def hash(self) -> bytes:
        h = good_hash(b"career")
        h.update(self.career.encode("UTF-8"))
        h.update(b"==" if self.equal else b"!=")
        return h.digest()


class ReqCourse(BaseExpr, frozen=True):
    """
    Require the student to have taken a course in the previous semesters.
    """

    expr: Literal["req"] = Field(default="req", const=True)

    code: str

    # Is this requirement a corequirement?
    coreq: bool

    def __str__(self) -> str:
        return f"{self.code}(c)" if self.coreq else self.code

    @cached_property
    def hash(self) -> bytes:
        h = good_hash(b"req")
        h.update(self.code.encode("UTF-8"))
        h.update(b"c" if self.coreq else b" ")
        return h.digest()


Atom = Const | MinCredits | ReqLevel | ReqSchool | ReqProgram | ReqCareer | ReqCourse

Operator = And | Or

Expr = Annotated[
    Operator | Atom,
    Field(discriminator="expr"),
]

And.update_forward_refs()
Or.update_forward_refs()
Const.update_forward_refs()
MinCredits.update_forward_refs()
ReqLevel.update_forward_refs()
ReqSchool.update_forward_refs()
ReqProgram.update_forward_refs()
ReqCareer.update_forward_refs()
ReqCourse.update_forward_refs()


class AndClause(And, frozen=True):
    children: tuple[Atom, ...]


class DnfExpr(Or, frozen=True):
    children: tuple[AndClause, ...]


def map_atoms(expr: Expr, map: Callable[[Atom], Atom]):
    """
    Replace the atoms of the expression according to `apply`.
    Returns a new expression, leaving the original unmodified.
    """
    if isinstance(expr, Operator):
        # Recursively replace atoms
        changed = False
        new_children: list[Expr] = []
        for child in expr.children:
            new_child = map_atoms(child, map)
            new_children.append(new_child)
            if new_child is not child:
                changed = True
        return BaseOp.create(expr.neutral, tuple(new_children)) if changed else expr
    # Replace this atom
    return map(expr)
