from abc import ABC
from dataclasses import dataclass
from ..diagnostic import DiagnosticErr, DiagnosticWarn, ValidationResult
from ...plan import ClassIndex, EquivalenceId, PseudoCourse, ValidatablePlan
from ...courseinfo import CourseDetails, CourseInfo
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
from typing import Callable, Optional, Type, Union, ClassVar
from .simplify import simplify


@dataclass
class CourseInstance:
    """
    An instance of a course, with a student and semester associated with it.
    In particular, the course index is a (semester, index within semester) pair.
    """

    course: PseudoCourse
    index: ClassIndex


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
            for i, course in enumerate(plan.classes[sem]):
                # Add this class to the map
                code = course.code
                if isinstance(course, EquivalenceId):
                    equiv = courseinfo.try_equiv(course.code)
                    if (
                        equiv is not None
                        and equiv.is_homogeneous
                        and len(equiv.courses) >= 1
                    ):
                        code = equiv.courses[0]
                if code not in classes:
                    classes[code] = CourseInstance(
                        course, index=ClassIndex(semester=sem, position=i)
                    )
                # Accumulate credits
                if isinstance(course, EquivalenceId):
                    creds += course.credits
                else:
                    # TODO: Double-check that credits always accumulate, even for
                    # duplicate courses
                    info = courseinfo.try_course(course.code)
                    if info is not None:
                        creds += info.credits
            acc_credits.append(creds)
        self.courseinfo = courseinfo
        self.classes = classes
        self.approved_credits = acc_credits
        self.plan = plan

    def validate(self, out: ValidationResult):
        ambiguous_codes: list[str] = []
        for sem in range(self.plan.next_semester, len(self.plan.classes)):
            sem_credits: int = 0

            for i, courseid in enumerate(self.plan.classes[sem]):
                index = ClassIndex(semester=sem, position=i)
                if isinstance(courseid, EquivalenceId):
                    equiv = self.courseinfo.try_equiv(courseid.code)
                    if equiv is None:
                        out.add(
                            UnknownCourseErr(
                                code=courseid.code, index=index
                            )
                        )
                        continue
                    elif equiv.is_homogeneous and len(equiv.courses) >= 1:
                        code = equiv.courses[0]
                    else:
                        ambiguous_codes.append(courseid.code)
                        sem_credits += courseid.credits
                        continue
                else:
                    code = courseid.code

                course = self.courseinfo.try_course(code)
                if course is None:
                    out.add(UnknownCourseErr(code=code, index=index))
                    continue

                inst = self.classes[course.code]
                self.diagnose(out, inst, course.deps)
                self.check_availability(out, inst, course)
                sem_credits += course.credits

            self.check_max_credits(out, semester=sem, credits=sem_credits)

        if ambiguous_codes:
            out.add(AmbiguousCoursesErr(codes=ambiguous_codes))

    def check_availability(
        self,
        out: ValidationResult,
        inst: CourseInstance,
        details: CourseDetails,
    ):
        if details.is_available:
            # TODO: check for TAV semester
            if not details.semestrality[inst.index.semester % 2]:
                out.add(SemestralityWarn(code=inst.course.code, index=inst.index))
        else:
            out.add(CourseUnavailableWarn(code=inst.course.code, index=inst.index))

    def check_max_credits(self, out: ValidationResult, semester: int, credits: int):
        if max_creds_err := SemesterErrHandler.check_error(
            semester=semester, credits=credits
        ):
            out.add(max_creds_err)

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
                    and not self.courseinfo.is_course_available(atom.code)
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
        out.add(
            RequirementErr(code=inst.course.code, index=inst.index, missing=missing)
        )


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
        return ctx.approved_credits[cl.index.semester] >= expr.min_credits
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
            return req_cl.index.semester <= cl.index.semester
        else:
            return req_cl.index.semester < cl.index.semester
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


class SemestralityWarn(DiagnosticWarn):
    index: ClassIndex
    code: str

    def course_index(self) -> Optional[ClassIndex]:
        return self.index

    def message(self) -> str:
        return (
            f"El curso {self.code} usualmente no se dicta en"
            f" {self.semester_type()} semestres."
        )

    def semester_type(self):
        if self.index.semester % 2 == 0:
            return "primeros"
        return "segundos"


class CourseUnavailableWarn(DiagnosticWarn):
    index: ClassIndex
    code: str

    def course_index(self) -> Optional[ClassIndex]:
        return self.index

    def message(self) -> str:
        return (
            f"El curso {self.code} no se ha dictado en mucho tiempo y probablemente"
            + " no se siga dictando"
        )


class AmbiguousCoursesErr(DiagnosticErr):
    codes: list[str]

    def first(self) -> str:
        return self.codes[0]

    def message(self) -> str:
        if len(self.codes) == 1:
            return f"Es necesario escoger un curso en el bloque {self.codes[0]}"
        return f"Es necesario escoger cursos en los bloques {', '.join(self.codes)}"


class CourseErr(DiagnosticErr, ABC):
    code: str
    index: ClassIndex

    def course_index(self) -> Optional[ClassIndex]:
        return self.index


class UnknownCourseErr(CourseErr):
    def message(self) -> str:
        return f"El curso {self.code} es desconocido. Revisa la sigla."


class RequirementErr(CourseErr):
    missing: Expr

    def message(self) -> str:
        return f"Requisitos insatisfechos para {self.code}, se necesita: {self.missing}"


class SemesterErrHandler:
    # TODO: the threadhold should depend on the amount of approved/dropped credits

    @staticmethod
    def check_error(
        semester: int, credits: int
    ) -> Union["MaxCreditsErr", "MaxCreditsWarn", None]:
        if credits > MaxCreditsErr.max_credits:
            return MaxCreditsErr(semester=semester)
        if credits > MaxCreditsWarn.max_credits:
            return MaxCreditsWarn(semester=semester)
        return None


class MaxCreditsErr(DiagnosticErr):
    """
    Occurs when the amount of credits in a semester is greater than a certain threshold.
    """

    max_credits: ClassVar[int] = 65
    semester: int

    def message(self) -> str:
        return (
            f"El semestre {self.semester + 1} sobrepasa el máximo de {self.max_credits}"
            " créditos permitido"
        )


class MaxCreditsWarn(DiagnosticWarn):
    """
    Warns when the amount of credits in a semester is greater than a certain threshold.
    """

    max_credits: ClassVar[int] = 55
    semester: int

    def message(self) -> str:
        return (
            f"El semestre {self.semester + 1} sobrepasa los {self.max_credits} créditos"
            " (revisa los requisitos relevantes)"
        )
