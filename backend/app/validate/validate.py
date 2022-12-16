from .logic import (
    BaseOp,
    Const,
    ReqCourse,
    Expr,
    Level,
    MinCredits,
    Operator,
    ReqCareer,
    ReqLevel,
    ReqProgram,
    ReqSchool,
)
from pydantic import BaseModel
from typing import Optional, Type
from .simplify import simplify


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


class Class:
    """
    An instance of a course, with a student and semester associated with it.
    """

    code: str
    semester: int

    def __init__(self, code: str, semester: int):
        self.code = code
        self.semester = semester


class PlanContext:
    rules: "CourseRules"
    # A dictionary of classes and their respective semesters
    classes: dict[str, Class]
    # A list of accumulated total approved credits per semester
    # approved_credits[i] contains the amount of approved credits in the range [0, i)
    approved_credits: list[int]
    # Original validatable plan object.
    plan: "ValidatablePlan"

    def __init__(self, rules: "CourseRules", plan: "ValidatablePlan"):
        # Map from coursecode to class
        classes = {}
        # List of total approved credits per semester
        acc_credits = [0]
        # Iterate over semesters
        for sem in range(len(plan.classes)):
            creds = acc_credits[-1]
            # Iterate over classes in this semester
            for code in plan.classes[sem]:
                # Add this class to the map
                if code not in classes:
                    classes[code] = Class(code, sem)
                # Accumulate credits
                # TODO: Do repeated courses count towards this credit count?
                if code in rules.courses:
                    creds += rules.courses[code].credits
            acc_credits.append(creds)
        self.rules = rules
        self.classes = classes
        self.approved_credits = acc_credits
        self.plan = plan

    def validate(self) -> dict[str, str]:
        diags: dict[str, str] = {}
        for sem in range(self.plan.next_semester, len(self.plan.classes)):
            for code in self.plan.classes[sem]:
                if code not in self.rules.courses:
                    diags[code] = "Curso desconocido"
                    continue
                course = self.rules.courses[code]
                cl = self.classes[code]
                diag = self.diagnose(cl, course.requires)
                if diag is not None:
                    diags[code] = diag
        return diags

    def diagnose(self, cl: Class, expr: "Expr") -> Optional[str]:
        if is_satisfied(self, cl, expr):
            return None
        # Some requirement is not satisfied
        # Fill in satisfied requirements, and then simplify resulting expression to get
        # an indication of "what do I have to do in order to satisfy requirements"
        missing = simplify(
            strip_satisfied(
                self, cl, expr, fixed_nodes=(ReqSchool, ReqProgram, ReqCareer)
            )
        )
        if isinstance(missing, Const):
            missing = simplify(strip_satisfied(self, cl, expr, fixed_nodes=tuple()))
        # Show this expression
        return f"Requisitos faltantes: {missing}"


class ValidatablePlan(BaseModel):
    # Classes per semester.
    classes: list[list[str]]
    # The first semester to validate.
    # Semester before this semester are considered approved.
    next_semester: int
    # Academic level of the student
    level: Optional[Level] = None
    # Academic school (facultad) of the student
    school: Optional[str] = None
    # Academic program of the student (magisteres, doctorados, etc)
    program: Optional[str] = None
    # Career of the student
    career: Optional[str] = None

    def make_live(self, rules: CourseRules) -> PlanContext:
        return PlanContext(rules, self)

    def diagnose(self, rules: CourseRules) -> dict[str, str]:
        return self.make_live(rules).validate()


def is_satisfied(ctx: PlanContext, cl: Class, expr: Expr) -> bool:
    if isinstance(expr, Operator):
        ok = expr.neutral
        for child in expr.children:
            ok = expr.op(ok, is_satisfied(ctx, cl, child))
        return ok
    if isinstance(expr, MinCredits):
        return ctx.approved_credits[cl.semester] >= expr.min_credits
    if isinstance(expr, ReqLevel):
        if ctx.plan.level is None:
            # TODO: Does everybody have a level?
            # Should planner reject guests with courses that have level restrictions?
            return False
        # TODO: Is this a `>=` relationship or actually an `=` relationship?
        return ctx.plan.level.value >= expr.min_level
    if isinstance(expr, ReqSchool):
        return (ctx.plan.school == expr.school) == expr.equal
    if isinstance(expr, ReqProgram):
        return (ctx.plan.program == expr.program) == expr.equal
    if isinstance(expr, ReqCareer):
        return (ctx.plan.career == expr.career) == expr.equal
    if isinstance(expr, ReqCourse):
        if expr.code not in ctx.classes:
            return False
        req_cl = ctx.classes[expr.code]
        if expr.coreq:
            return req_cl.semester <= cl.semester
        else:
            return req_cl.semester < cl.semester
    # assert isinstance(expr, Const)
    return expr.value


def strip_satisfied(
    ctx: PlanContext,
    cl: Class,
    expr: Expr,
    fixed_nodes: tuple[Type[Expr], ...] = tuple(),
) -> Expr:
    """
    Replace nodes that are already satisfied by a constant `True`.
    This results in an expression that represents what remains to be satisfied.
    Simplify the expression afterwards!

    `fixed_nodes` specifies types of node to consider as un-changeable.
    For example, the `ReqCareer` node could be fixed, because you do not expect the
    user to change their career in order to take a course.
    """
    if isinstance(expr, fixed_nodes):
        return Const(value=is_satisfied(ctx, cl, expr))
    if isinstance(expr, Operator):
        changed = False
        new_children: list[Expr] = []
        for child in expr.children:
            new_child = strip_satisfied(ctx, cl, child, fixed_nodes)
            new_children.append(new_child)
            if new_child is not child:
                changed = True
        if changed:
            return BaseOp.create(expr.neutral, tuple(new_children))
        else:
            return expr
    if is_satisfied(ctx, cl, expr):
        return Const(value=True)
    else:
        return expr
