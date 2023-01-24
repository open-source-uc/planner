from abc import ABC
from dataclasses import dataclass
from ..diagnostic import DiagnosticErr, ValidationResult
from ...plan import EquivalenceId, PseudoCourse, ValidatablePlan
from ...courseinfo import CourseInfo
from .logic import (
    Atom,
    BaseOp,
    Const,
    ReqCourse,
    Expr,
    MinCredits,
    Operator,
    ReqCareer,
    ReqLevel,
    ReqProgram,
    ReqSchool,
)
from typing import Callable, Optional, Type
from .simplify import simplify


@dataclass
class CourseInstance:
    """
    An instance of a course, with a student and semester associated with it.
    """

    course: PseudoCourse
    semester: int


class PlanContext:
    """
    Basically a `ValidatablePlan` augmented with context that the `CourseRules` provide,
    and with some additional preprocessing to make validation convenient.
    For example, `PlanContext` has a dictionary from course code to
    semester-in-which-the-course-is-taken, a dict that is useful when validating.
    """

    courseinfo: CourseInfo
    # A dictionary of classes and their respective semesters
    classes: dict[str, CourseInstance]
    # A list of accumulated total approved credits per semester
    # approved_credits[i] contains the amount of approved credits in the range [0, i)
    approved_credits: list[int]
    # Original validatable plan object.
    plan: ValidatablePlan

    def __init__(self, courseinfo: CourseInfo, plan: ValidatablePlan):
        # Map from coursecode to course instance
        classes = {}
        # List of total approved credits per semester
        acc_credits = [0]
        # Iterate over semesters
        for sem in range(len(plan.classes)):
            creds = acc_credits[-1]
            # Iterate over classes in this semester
            for course in plan.classes[sem]:
                # Add this class to the map
                code = course.code
                if isinstance(course, EquivalenceId):
                    equiv = courseinfo.equiv(course.code)
                    if equiv.is_homogeneous and len(equiv.courses) >= 1:
                        code = equiv.courses[0]
                if code not in classes:
                    classes[code] = CourseInstance(course, sem)
                # Accumulate credits
                if isinstance(course, EquivalenceId):
                    creds += course.credits
                else:
                    # TODO: Credits only accumulate if they count towards the
                    # curriculum!!
                    creds += courseinfo.course(course.code).credits
            acc_credits.append(creds)
        self.courseinfo = courseinfo
        self.classes = classes
        self.approved_credits = acc_credits
        self.plan = plan

    def validate(self, out: ValidationResult):
        for sem in range(self.plan.next_semester, len(self.plan.classes)):
            for courseid in self.plan.classes[sem]:
                if isinstance(courseid, EquivalenceId):
                    equiv = self.courseinfo.equiv(courseid.code)
                    if equiv.is_homogeneous and len(equiv.courses) >= 1:
                        course = self.courseinfo.course(equiv.courses[0])
                    else:
                        out.add(AmbiguousCourseErr(code=courseid.code))
                        continue
                else:
                    course = self.courseinfo.course(courseid.code)
                inst = self.classes[course.code]
                self.diagnose(out, inst, course.deps)

    def diagnose(self, out: ValidationResult, inst: CourseInstance, expr: "Expr"):
        if is_satisfied(self, inst, expr):
            return None
        # Some requirement is not satisfied
        # Fill in satisfied requirements, and then simplify resulting expression to get
        # an indication of "what do I have to do in order to satisfy requirements"
        # Stage 1: ignore unavailable courses and fix school/program/career
        missing = simplify(
            fold_atoms(
                self,
                inst,
                expr,
                lambda atom, sat: sat
                or isinstance(atom, (ReqSchool, ReqProgram, ReqCareer))
                or (
                    isinstance(atom, ReqCourse)
                    and not self.courseinfo.course(atom.code).is_available
                ),
            )
        )
        # Stage 2: allow unavailable courses
        if isinstance(missing, Const):
            missing = simplify(
                fold_atoms(
                    self,
                    inst,
                    expr,
                    lambda atom, sat: sat
                    or isinstance(atom, (ReqSchool, ReqProgram, ReqCareer)),
                )
            )
        # Stage 3: allow changing everything
        if isinstance(missing, Const):
            missing = simplify(fold_atoms(self, inst, expr, lambda atom, sat: sat))
        # Show this expression
        out.add(RequirementErr(code=inst.course.code, missing=missing))


def is_satisfied(ctx: PlanContext, cl: CourseInstance, expr: Expr) -> bool:
    """
    Core logic to check whether an expression is satisfied by a student and their plan.
    """
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
        return ctx.plan.level.value >= expr.min_level.value
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


def fold_atoms(
    ctx: PlanContext,
    cl: CourseInstance,
    expr: Expr,
    do_replace: Callable[[Atom, bool], bool],
) -> Expr:
    if isinstance(expr, Operator):
        # Recursively replace atoms
        changed = False
        new_children: list[Expr] = []
        for child in expr.children:
            new_child = fold_atoms(ctx, cl, child, do_replace)
            new_children.append(new_child)
            if new_child is not child:
                changed = True
        if changed:
            return BaseOp.create(expr.neutral, tuple(new_children))
    else:
        # Maybe replace this atom by its truth value
        truth = is_satisfied(ctx, cl, expr)
        if do_replace(expr, truth):
            # Fold this atom into its constant truth value
            return Const(value=truth)
    return expr


def strip_satisfied(
    ctx: PlanContext,
    cl: CourseInstance,
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


def is_course_known(courseinfo: CourseInfo, courseid: PseudoCourse) -> bool:
    if isinstance(courseid, EquivalenceId):
        return courseinfo.try_equiv(courseid.code) is not None
    else:
        return courseinfo.try_course(courseid.code) is not None


def sanitize_plan(courseinfo: CourseInfo, out: ValidationResult, plan: ValidatablePlan):
    unknown = False
    for semester in plan.classes:
        for courseid in semester:
            if not is_course_known(courseinfo, courseid):
                unknown = True

    if unknown:
        copy = plan.copy()
        copy.classes = []
        for semester in plan.classes:
            new_sem: list[PseudoCourse] = []
            for courseid in semester:
                if is_course_known(courseinfo, courseid):
                    new_sem.append(courseid)
                else:
                    out.add(UnknownCourseErr(code=courseid.code))
            copy.classes.append(new_sem)
        return copy
    else:
        return plan


class CourseErr(DiagnosticErr, ABC):
    code: str

    def course_code(self) -> Optional[str]:
        return self.code


class UnknownCourseErr(CourseErr):
    def message(self) -> str:
        return "Curso desconocido"


class AmbiguousCourseErr(CourseErr):
    def message(self) -> str:
        return "Curso requiere desambiguacion"


class RequirementErr(CourseErr):
    missing: Expr

    def message(self) -> str:
        return f"Requisitos faltantes: {self.missing}"
