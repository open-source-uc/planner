"""
Implements logical expressions in the context of course requirements.
"""

from collections.abc import Callable
from hashlib import blake2b as good_hash
from typing import Annotated, Any, ClassVar, Literal

from pydantic import BaseModel, Field


def create_op(neutral: bool, children: tuple["Expr", ...]) -> "Operator":
    """
    Build an AND node or an OR node in a generic way, using the neutral element to
    distinguish between them.
    In other words, if `neutral` is true, build an AND node, otherwise build an OR
    node.
    """
    return And(children=children) if neutral else Or(children=children)


def _remove_hash_from_schema(schema: dict[str, Any]) -> None:
    del schema.get("properties", {})["hash"]


class And(BaseModel, frozen=True, schema_extra=_remove_hash_from_schema):
    """
    Logical AND connector.
    Only satisfied if all of its children are satisfied.
    """

    hash: bytes = Field(default=b"", exclude=True, repr=False)
    expr: Literal["and"] = Field(default="and", const=True)
    neutral: ClassVar[bool] = True
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


class Or(BaseModel, frozen=True, schema_extra=_remove_hash_from_schema):
    """
    Logical OR connector.
    Only satisfied if at least one of its children is satisfied.
    """

    hash: bytes = Field(default=b"", exclude=True, repr=False)
    expr: Literal["or"] = Field(default="or", const=True)
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


class Const(BaseModel, frozen=True, schema_extra=_remove_hash_from_schema):
    """
    A constant, fixed value of True or False.
    """

    hash: bytes = Field(default=b"", exclude=True, repr=False)
    expr: Literal["const"] = Field(default="const", const=True)
    value: bool

    def __str__(self) -> str:
        return str(self.value)


class MinCredits(BaseModel, frozen=True, schema_extra=_remove_hash_from_schema):
    """
    A restriction that is only satisfied if the total amount of credits in the previous
    semesters is over a certain threshold.
    """

    hash: bytes = Field(default=b"", exclude=True, repr=False)
    expr: Literal["cred"] = Field(default="cred", const=True)

    min_credits: int

    def __str__(self) -> str:
        return f"(Creditos >= {self.min_credits})"


class ReqLevel(BaseModel, frozen=True, schema_extra=_remove_hash_from_schema):
    """
    Express that this course requires a certain academic level.
    """

    hash: bytes = Field(default=b"", exclude=True, repr=False)
    expr: Literal["lvl"] = Field(default="lvl", const=True)

    # Takes the values: "Pregrado", "Postitulo", "Magister", "Doctorado".
    level: str

    # Require equality or inequality?
    equal: bool

    def __str__(self) -> str:
        eq = "=" if self.equal else "!="
        return f"(Nivel {eq} {self.level})"


class ReqSchool(BaseModel, frozen=True, schema_extra=_remove_hash_from_schema):
    """
    Express that this course requires the student to belong to a particular school.
    """

    hash: bytes = Field(default=b"", exclude=True, repr=False)
    expr: Literal["school"] = Field(default="school", const=True)

    school: str

    # Require equality or inequality?
    equal: bool

    def __str__(self) -> str:
        eq = "=" if self.equal else "!="
        return f"(Facultad {eq} {self.school})"


class ReqProgram(BaseModel, frozen=True, schema_extra=_remove_hash_from_schema):
    """
    Express that this course requires the student to belong to a particular program.
    """

    hash: bytes = Field(default=b"", exclude=True, repr=False)
    expr: Literal["program"] = Field(default="program", const=True)

    program: str

    # Require equality or inequality?
    equal: bool

    def __str__(self) -> str:
        eq = "=" if self.equal else "!="
        return f"(Programa {eq} {self.program})"


class ReqCareer(BaseModel, frozen=True, schema_extra=_remove_hash_from_schema):
    """
    Express that this course requires the student to belong to a particular career.
    """

    hash: bytes = Field(default=b"", exclude=True, repr=False)
    expr: Literal["career"] = Field(default="career", const=True)

    career: str

    # Require equality or inequality?
    equal: bool

    def __str__(self) -> str:
        eq = "=" if self.equal else "!="
        return f"(Carrera {eq} {self.career})"


class ReqCourse(BaseModel, frozen=True, schema_extra=_remove_hash_from_schema):
    """
    Require the student to have taken a course in the previous semesters.
    """

    hash: bytes = Field(default=b"", exclude=True, repr=False)
    expr: Literal["req"] = Field(default="req", const=True)

    code: str

    # Is this requirement a corequirement?
    coreq: bool

    def __str__(self) -> str:
        return f"{self.code}(c)" if self.coreq else self.code


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


class AndClause(And, frozen=True, schema_extra=_remove_hash_from_schema):
    children: tuple[Atom, ...]


class DnfExpr(Or, frozen=True, schema_extra=_remove_hash_from_schema):
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
        return create_op(expr.neutral, tuple(new_children)) if changed else expr
    # Replace this atom
    return map(expr)


def hash_expr(expr: Expr) -> bytes:
    hash = expr.hash
    if hash == b"":
        if isinstance(expr, And):
            h = good_hash(b"y")
            for child in expr.children:
                h.update(child.hash)
            hash = h.digest()
        elif isinstance(expr, Or):
            h = good_hash(b"o")
            for child in expr.children:
                h.update(child.hash)
            hash = h.digest()
        elif isinstance(expr, Const):
            h = good_hash(b"one" if expr.value else b"zero")
            hash = h.digest()
        elif isinstance(expr, MinCredits):
            h = good_hash(b"cred")
            h.update(expr.min_credits.to_bytes(4))
            hash = h.digest()
        elif isinstance(expr, ReqLevel):
            h = good_hash(b"level")
            h.update(expr.level.encode("UTF-8"))
            h.update(b"==" if expr.equal else b"!=")
            hash = h.digest()
        elif isinstance(expr, ReqSchool):
            h = good_hash(b"school")
            h.update(expr.school.encode("UTF-8"))
            h.update(b"==" if expr.equal else b"!=")
            hash = h.digest()
        elif isinstance(expr, ReqProgram):
            h = good_hash(b"program")
            h.update(expr.program.encode("UTF-8"))
            h.update(b"==" if expr.equal else b"!=")
            hash = h.digest()
        elif isinstance(expr, ReqCareer):
            h = good_hash(b"career")
            h.update(expr.career.encode("UTF-8"))
            h.update(b"==" if expr.equal else b"!=")
            hash = h.digest()
        else:
            # assert isinstance(expr, ReqCourse)
            h = good_hash(b"req")
            h.update(expr.code.encode("UTF-8"))
            h.update(b"c" if expr.coreq else b" ")
            hash = h.digest()

    expr.__dict__["hash"] = hash
    assert expr.hash == hash
    return hash
