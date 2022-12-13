from abc import abstractmethod
from enum import Enum
from .logic import Atom, And, Const, Operator, Or
from pydantic import BaseModel, Field
from typing import Annotated, Literal, Optional, Union


class Level(Enum):
    """
    An academic level.
    """

    # TODO: Confirm this order, is it correct?
    PREGRADO = 1
    POSTITULO = 2
    MAGISTER = 3
    DOCTORADO = 4


class AcademicAtom(Atom):
    """
    An boolean variable that may be true or false for a particular student, depending
    only on the course and student context.
    """

    @abstractmethod
    def is_satisfied(self, ctx: "diagnostic.PlanContext", cl: "diagnostic.Class"):
        pass


class MinCredits(Atom):
    """
    A restriction that is only satisfied if the total amount of credits in the previous
    semesters is over a certain threshold.
    """

    expr: Literal["creds"] = "creds"

    min_credits: int

    def __str__(self):
        return f"(creditos aprobados >= {self.min_credits})"

    def calc_hash(self) -> int:
        return hash(("creds", self.min_credits))

    def is_satisfied(self, ctx: "diagnostic.PlanContext", cl: "diagnostic.Class"):
        return ctx.approved_credits[cl.semester] >= self.min_credits


class ReqLevel(Atom):
    """
    Express that this course requires a certain academic level.
    """

    expr: Literal["lvl"] = "lvl"

    min_level: Level
    __hash: Optional[int] = Field(None, repr=False)

    def __str__(self):
        return f"(nivel = {self.min_level})"

    def calc_hash(self):
        return hash(("lvl", self.min_level))

    def is_satisfied(self, ctx: "diagnostic.PlanContext", cl: "diagnostic.Class"):
        if ctx.plan.level is None:
            # TODO: Does everybody have a level?
            # Should planner reject guests with courses that have level restrictions?
            return False
        # TODO: Is this a `>=` relationship or actually an `=` relationship?
        return ctx.plan.level.value >= self.min_level


class ReqSchool(Atom):
    """
    Express that this course requires the student to belong to a particular school.
    """

    expr: Literal["school"] = "school"

    school: str

    # Require equality or inequality?
    equal: bool

    def __str__(self):
        eq = "=" if self.equal else "!="
        return f"(facultad {eq} {self.school})"

    def calc_hash(self) -> int:
        return hash(("school", self.school, self.equal))

    def is_satisfied(self, ctx: "diagnostic.PlanContext", cl: "diagnostic.Class"):
        return (ctx.plan.school == self.school) == self.equal


class ReqProgram(Atom):
    """
    Express that this course requires the student to belong to a particular program.
    """

    expr: Literal["program"] = "program"

    program: str

    # Require equality or inequality?
    equal: bool

    def __str__(self):
        eq = "=" if self.equal else "!="
        return f"(programa {eq} {self.program})"

    def calc_hash(self) -> int:
        return hash(("program", self.program, self.equal))

    def is_satisfied(self, ctx: "diagnostic.PlanContext", cl: "diagnostic.Class"):
        return (ctx.plan.program == self.program) == self.equal


class ReqCareer(Atom):
    """
    Express that this course requires the student to belong to a particular career.
    """

    expr: Literal["career"] = "career"

    career: str

    # Require equality or inequality?
    equal: bool

    def __str__(self):
        eq = "=" if self.equal else "!="
        return f"(carrera {eq} {self.career})"

    def calc_hash(self) -> int:
        return hash(("career", self.career, self.equal))

    def is_satisfied(self, ctx: "diagnostic.PlanContext", cl: "diagnostic.Class"):
        return (ctx.plan.career == self.career) == self.equal


class CourseRequirement(Atom):
    """
    Require the student to have taken a course in the previous semesters.
    """

    expr: Literal["req"] = "req"

    code: str

    # Is this requirement a corequirement?
    coreq: bool

    def __str__(self):
        if self.coreq:
            return f"{self.code}(c)"
        else:
            return self.code

    def calc_hash(self) -> int:
        return hash(("req", self.code, self.coreq))

    def is_satisfied(self, ctx: "diagnostic.PlanContext", cl: "diagnostic.Class"):
        if self.code not in ctx.classes:
            return False
        req_cl = ctx.classes[self.code]
        if self.coreq:
            return req_cl.semester <= cl.semester
        else:
            return req_cl.semester < cl.semester


Expr = Annotated[
    Union[
        Operator,
        And,
        Or,
        Const,
        MinCredits,
        ReqLevel,
        ReqSchool,
        ReqProgram,
        ReqCareer,
        CourseRequirement,
    ],
    Field(discriminator="expr"),
]


class Course(BaseModel):
    """
    A single course, with an associated code.
    This course is not "instantiated", it is an abstract course prototype.
    """

    code: str
    credits: int
    requires: Expr


class CourseRules(BaseModel):
    """
    A collection of courses with their own requirements.
    """

    courses: dict[str, Course]


from . import diagnostic

MinCredits.update_forward_refs()
ReqLevel.update_forward_refs()
ReqSchool.update_forward_refs()
ReqProgram.update_forward_refs()
ReqCareer.update_forward_refs()
CourseRequirement.update_forward_refs()
