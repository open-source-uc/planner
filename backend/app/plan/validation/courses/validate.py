from dataclasses import dataclass
from ....user.info import StudentContext
from ...course import ConcreteId, EquivalenceId
from ..diagnostic import (
    AmbiguousCourseErr,
    CourseRequirementErr,
    SemesterCreditsErr,
    SemesterCreditsWarn,
    SemestralityWarn,
    UnavailableCourseWarn,
    UnknownCourseErr,
    ValidationResult,
)
from ...plan import ClassId, ValidatablePlan
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
from typing import Callable, Optional
from .simplify import simplify


@dataclass
class CourseInstance:
    """
    An instance of a course within a plan.
    Has a position (semester, index) within the plan.
    """

    code: str
    sem: int
    index: int


class ValidationContext:
    """
    Pre-processing of a validatable plan, created once and used to validate the course
    rules for all classes.
    """

    courseinfo: CourseInfo
    # A dictionary from course code to the first time the course appears in the plan.
    # This dictionary considers equivalencies (ie. some codes map to equivalent
    # courses).
    by_code: dict[str, CourseInstance]
    # Map from (semester, index) positions to class ids.
    class_ids: list[list[ClassId]]
    # A list of accumulated total approved credits per semester
    # approved_credits[i] contains the amount of approved credits in the range [0, i)
    approved_credits: list[int]
    # Original validatable plan object.
    plan: ValidatablePlan
    # User context, if any
    user_ctx: Optional[StudentContext]
    # On which semester to start validating requirements and other associated
    # validations.
    # Should be the first semester that has not yet been taken (ie. the semester after
    # the current one).
    start_validation_from: int

    def __init__(
        self,
        courseinfo: CourseInfo,
        plan: ValidatablePlan,
        user_ctx: Optional[StudentContext],
    ):
        # Map from coursecode to course instance
        self.by_code = {}
        for sem_i, sem in enumerate(plan.classes):
            for i, course in enumerate(sem):
                # Determine which courses are equivalent to this course
                equiv_codes = [course.code]
                info = courseinfo.try_course(course.code)
                if info is not None:
                    for equiv in info.banner_equivs:
                        equiv_codes.append(equiv)

                # Map the equivalent courses to this course instance
                course_inst = CourseInstance(code=course.code, sem=sem_i, index=i)
                for code in equiv_codes:
                    if code not in self.by_code:
                        self.by_code[code] = course_inst

        # Map from class positions to class ids
        rep_counts: dict[str, int] = {}
        self.class_ids = []
        for sem in plan.classes:
            mapping: list[ClassId] = []
            for course in sem:
                rep_idx = rep_counts.get(course.code, 0)
                mapping.append(ClassId(code=course.code, instance=rep_idx))
                rep_counts[course.code] = rep_idx + 1
            self.class_ids.append(mapping)

        # Accumulate approved credits by semester
        self.approved_credits = [0]
        credit_acc = 0
        for sem in plan.classes:
            for course in sem:
                credit_acc += courseinfo.get_credits(course) or 0
            self.approved_credits.append(credit_acc)

        # The first semester where courses have not yet been taken
        self.start_validation_from = 0 if user_ctx is None else user_ctx.next_semester

        # Context
        self.courseinfo = courseinfo
        self.plan = plan
        self.user_ctx = user_ctx

    def validate_all_unknown(self, out: ValidationResult):
        """
        Generate a diagnostic if there are unknown courses.
        """
        unknown: list[ClassId] = []
        for sem_i, sem in enumerate(self.plan.classes):
            for i, course in enumerate(sem):
                if isinstance(course, EquivalenceId):
                    if self.courseinfo.try_equiv(course.code) is None:
                        unknown.append(self.class_ids[sem_i][i])
                else:
                    if course.failed is not None:
                        # Ignore failed courses
                        continue
                    if self.courseinfo.try_course(course.code) is None:
                        unknown.append(self.class_ids[sem_i][i])
        if unknown:
            out.add(UnknownCourseErr(associated_to=unknown))

    def validate_all_ambiguous(self, out: ValidationResult):
        """
        Generate a diagnostic if there are ambiguous equivalences that must be
        disambiguated to guarantee proper validation.
        """
        ambiguous: list[ClassId] = []
        for sem_i, sem in enumerate(self.plan.classes):
            for i, course in enumerate(sem):
                if isinstance(course, EquivalenceId):
                    info = self.courseinfo.try_equiv(course.code)
                    if info is not None and not info.is_unessential:
                        ambiguous.append(self.class_ids[sem_i][i])
        if ambiguous:
            out.add(AmbiguousCourseErr(associated_to=ambiguous))

    def validate_all_availability(self, out: ValidationResult):
        """
        Validate the availability and semestrality of all courses.
        """
        unavailable: list[ClassId] = []
        only_on_sem: list[list[ClassId]] = [[], []]
        for sem_i in range(self.start_validation_from, len(self.plan.classes)):
            for i, course in enumerate(self.plan.classes[sem_i]):
                if isinstance(course, ConcreteId):
                    info = self.courseinfo.try_course(course.code)
                    if info is not None:
                        if not info.is_available:
                            # This course is plain unavailable
                            unavailable.append(self.class_ids[sem_i][i])
                        elif (
                            not info.semestrality[sem_i % 2]
                            and info.semestrality[(sem_i + 1) % 2]
                        ):
                            # This course is only available on the other semester
                            only_on_sem[(sem_i + 1) % 2].append(
                                self.class_ids[sem_i][i]
                            )
        if unavailable:
            out.add(UnavailableCourseWarn(associated_to=unavailable))
        for k in range(2):
            if only_on_sem[k]:
                out.add(
                    SemestralityWarn(associated_to=only_on_sem[k], only_available_on=k)
                )

    def validate_max_credits(self, out: ValidationResult):
        """
        Validate that there are no semester with an excess of credits.
        """

        # Students can only take this amount of credits if they meet certain criteria.
        # Currently, that criteria is not failing any course in the previous X
        # semesters.
        # TODO: Actually check this criteria, and apply validations depending on user
        # context.
        SOFT_MAX = 55
        # Students can't take over this amount of credits without special authorization.
        HARD_MAX = 65

        for sem_i in range(self.start_validation_from, len(self.plan.classes)):
            sem_credits = 0
            for course in self.plan.classes[sem_i]:
                sem_credits += self.courseinfo.get_credits(course) or 0
                if sem_credits > HARD_MAX:
                    out.add(
                        SemesterCreditsErr(
                            associated_to=[sem_i],
                            max_allowed=HARD_MAX,
                            actual=sem_credits,
                        )
                    )
                elif sem_credits > SOFT_MAX:
                    out.add(
                        SemesterCreditsWarn(
                            associated_to=[sem_i],
                            max_recommended=SOFT_MAX,
                            actual=sem_credits,
                        )
                    )

    def validate_all_dependencies(self, out: ValidationResult):
        """
        Validate the dependencies of all non-passed courses.
        """
        for sem_i in range(self.start_validation_from, len(self.plan.classes)):
            for i, course in enumerate(self.plan.classes[sem_i]):
                # Get a concrete course code from the given courseid
                if isinstance(course, EquivalenceId):
                    info = self.courseinfo.try_equiv(course.code)
                    if (
                        info is not None
                        and info.is_homogeneous
                        and len(info.courses) >= 1
                    ):
                        code = info.courses[0]
                    else:
                        continue
                else:
                    code = course.code

                # Validate the dependencies for this course
                info = self.courseinfo.try_course(code)
                if info is not None:
                    self.validate_dependencies_for(
                        out, CourseInstance(code, sem_i, i), info.deps
                    )

    def validate_all(self, out: ValidationResult):
        """
        Execute all validations, shoving any diagnostics into `out`.
        """
        self.validate_all_unknown(out)
        self.validate_all_ambiguous(out)
        self.validate_all_availability(out)
        self.validate_max_credits(out)
        self.validate_all_dependencies(out)

    def validate_dependencies_for(
        self, out: ValidationResult, inst: CourseInstance, expr: "Expr"
    ):
        """
        Validate the requirements for the course `inst`.
        """
        if is_satisfied(self, inst, expr):
            return None
        # Some requirement is not satisfied
        # Fill in satisfied requirements, and then simplify resulting expression to get
        # an indication of "what do I have to do in order to satisfy requirements"
        # Stage 1: ignore unavailable courses and fix school/program/career
        missing = simplify(
            set_atoms_in_stone_if(
                self,
                inst,
                expr,
                lambda atom, sat: sat
                or isinstance(atom, (ReqSchool, ReqProgram, ReqCareer))
                or (
                    isinstance(atom, ReqCourse)
                    and not is_course_indirectly_available(self.courseinfo, atom.code)
                ),
            )
        )
        # Stage 2: allow unavailable courses
        if isinstance(missing, Const):
            missing = simplify(
                set_atoms_in_stone_if(
                    self,
                    inst,
                    expr,
                    lambda atom, sat: sat
                    or isinstance(atom, (ReqSchool, ReqProgram, ReqCareer)),
                )
            )
        # Stage 3: allow changing everything
        if isinstance(missing, Const):
            # Only set atoms in stone if they are satisfied (ie. leave all unsatisfied
            # requirements as free variables)
            missing = simplify(
                set_atoms_in_stone_if(self, inst, expr, lambda atom, sat: sat)
            )
        # Map missing courses to their newest equivalent versions
        missing_equivalents = map_atoms(missing, self.map_to_equivalent)
        # Show this expression
        out.add(
            CourseRequirementErr(
                associated_to=[self.class_ids[inst.sem][inst.index]],
                missing=missing,
                modernized_missing=missing_equivalents,
            )
        )

    def map_to_equivalent(self, atom: Atom) -> Atom:
        if isinstance(atom, ReqCourse):
            info = self.courseinfo.try_course(atom.code)
            if info is not None and info.canonical_equiv != atom.code:
                return ReqCourse(code=info.canonical_equiv, coreq=atom.coreq)
        return atom


def is_satisfied(ctx: ValidationContext, cl: CourseInstance, expr: Expr) -> bool:
    """
    Core logic to check whether an expression is satisfied by a student and their plan.
    """
    if isinstance(expr, Operator):
        ok = expr.neutral
        for child in expr.children:
            ok = expr.op(ok, is_satisfied(ctx, cl, child))
        return ok
    if isinstance(expr, MinCredits):
        return ctx.approved_credits[cl.sem] >= expr.min_credits
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
        if expr.code not in ctx.by_code:
            return False
        req_cl = ctx.by_code[expr.code]
        if expr.coreq:
            return req_cl.sem <= cl.sem
        else:
            return req_cl.sem < cl.sem
    # assert isinstance(expr, Const)
    return expr.value


def set_atoms_in_stone_if(
    ctx: ValidationContext,
    cl: CourseInstance,
    expr: Expr,
    should_set_in_stone: Callable[[Atom, bool], bool],
) -> Expr:
    """
    Call `should_set_in_stone` on all atoms of the expression (along with a boolean
    indicating whether they are currently satisfied or not).
    If it returns `True`, replace the atom with a constant boolean indicating its
    current satisfaction status ("sets the atom in stone").
    Returns a modified copy of `expr` (it does **not** modify `expr`).
    """
    if isinstance(expr, Operator):
        # Recursively replace atoms
        changed = False
        new_children: list[Expr] = []
        for child in expr.children:
            new_child = set_atoms_in_stone_if(ctx, cl, child, should_set_in_stone)
            new_children.append(new_child)
            if new_child is not child:
                changed = True
        if changed:
            return BaseOp.create(expr.neutral, tuple(new_children))
    else:
        # Maybe replace this atom by its truth value
        truth = is_satisfied(ctx, cl, expr)
        if should_set_in_stone(expr, truth):
            # Fold this atom into its constant truth value
            return Const(value=truth)
    return expr


def is_course_indirectly_available(courseinfo: CourseInfo, code: str):
    info = courseinfo.try_course(code)
    if info is None:
        return False
    if info.is_available:
        return True
    modernized_info = courseinfo.try_course(info.canonical_equiv)
    if modernized_info is not None and modernized_info.is_available:
        return True
    return False


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
        if changed:
            return BaseOp.create(expr.neutral, tuple(new_children))
        else:
            return expr
    else:
        # Replace this atom
        return map(expr)
