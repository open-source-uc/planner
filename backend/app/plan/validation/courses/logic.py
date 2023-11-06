"""
Implements logical expressions in the context of course requirements.
"""


from collections.abc import Callable
from functools import cached_property
from hashlib import blake2b as good_hash
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, Field


def create_op(neutral: bool, children: tuple["Expr", ...]) -> "Operator":
    """
    Build an AND node or an OR node in a generic way, using the neutral element to
    distinguish between them.
    In other words, if `neutral` is true, build an AND node, otherwise build an OR
    node.
    """
    return (
        And(expr="and", children=children)
        if neutral
        else Or(expr="or", children=children)
    )


class And(BaseModel, frozen=True):
    """
    Logical AND connector.
    Only satisfied if all of its children are satisfied.
    """

    expr: Literal["and"]
    neutral: ClassVar[Literal[True]] = True
    children: tuple["Expr", ...]

    def __str__(self) -> str:
        s = ""
        for child in self.children:
            if s != "":
                s += " y "
            if isinstance(child, Operator):
                s += f"({child})"
            else:
                s += str(child)
        return s

    @cached_property
    def hash(self) -> bytes:
        h = good_hash(b"y")
        for child in self.children:
            h.update(child.hash)
        return h.digest()


class Or(BaseModel, frozen=True):
    """
    Logical OR connector.
    Only satisfied if at least one of its children is satisfied.
    """

    expr: Literal["or"]
    neutral: ClassVar[bool] = False
    children: tuple["Expr", ...]

    def __str__(self) -> str:
        s = ""
        for child in self.children:
            if s != "":
                s += " o "
            if isinstance(child, Operator):
                s += f"({child})"
            else:
                s += str(child)
        return s

    @cached_property
    def hash(self) -> bytes:
        h = good_hash(b"o")
        for child in self.children:
            h.update(child.hash)
        return h.digest()


class Const(BaseModel, frozen=True):
    """
    A constant, fixed value of True or False.
    """

    expr: Literal["const"]
    value: bool

    def __str__(self) -> str:
        return str(self.value)

    @cached_property
    def hash(self) -> bytes:
        h = good_hash(b"one" if self.value else b"zero")
        return h.digest()


class MinCredits(BaseModel, frozen=True):
    """
    A restriction that is only satisfied if the total amount of credits in the previous
    semesters is over a certain threshold.
    """

    expr: Literal["cred"]

    min_credits: int

    def __str__(self) -> str:
        return f"(Creditos >= {self.min_credits})"

    @cached_property
    def hash(self) -> bytes:
        h = good_hash(b"cred")
        h.update(self.min_credits.to_bytes(4))
        return h.digest()


class ReqLevel(BaseModel, frozen=True):
    """
    Express that this course requires a certain academic level.
    """

    expr: Literal["lvl"]

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


class ReqSchool(BaseModel, frozen=True):
    """
    Express that this course requires the student to belong to a particular school.
    """

    expr: Literal["school"]

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


class ReqProgram(BaseModel, frozen=True):
    """
    Express that this course requires the student to belong to a particular program.
    """

    expr: Literal["program"]

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


class ReqCareer(BaseModel, frozen=True):
    """
    Express that this course requires the student to belong to a particular career.
    """

    expr: Literal["career"]

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


class ReqCourse(BaseModel, frozen=True):
    """
    Require the student to have taken a course in the previous semesters.
    """

    expr: Literal["req"]

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

And.model_rebuild()
Or.model_rebuild()
Const.model_rebuild()
MinCredits.model_rebuild()
ReqLevel.model_rebuild()
ReqSchool.model_rebuild()
ReqProgram.model_rebuild()
ReqCareer.model_rebuild()
ReqCourse.model_rebuild()


class AndClause(And, frozen=True):
    children: tuple[Atom, ...]


class DnfExpr(Or, frozen=True):
    children: tuple[AndClause, ...]


def map_atoms(expr: Expr, map: Callable[[Atom], Atom]) -> Expr:
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
        return create_op(expr.neutral, tuple(new_children)) if changed else expr
    # Replace this atom
    return map(expr)
