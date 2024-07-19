from collections.abc import Callable
from dataclasses import dataclass

from app.plan.course import ConcreteId, EquivalenceId, PseudoCourse
from app.plan.courseinfo import CourseInfo
from app.plan.plan import ClassId, ValidatablePlan
from app.plan.validation.courses.logic import (
    And,
    Atom,
    Const,
    Expr,
    MinCredits,
    Operator,
    Or,
    ReqCareer,
    ReqCourse,
    ReqLevel,
    ReqProgram,
    ReqSchool,
    map_atoms,
)
from app.plan.validation.courses.simplify import simplify
from app.plan.validation.diagnostic import (
    AmbiguousCourseWarn,
    CourseRequirementErr,
    SemesterCreditsDiag,
    SemestralityWarn,
    UnavailableCourseWarn,
    UnknownCourseErr,
    ValidationResult,
)
from app.user.info import StudentInfo

# Students can only take this amount of credits if they meet certain criteria.
# Currently, that criteria is not failing any course in the previous X
# semesters.
# TODO: Actually check this criteria, and apply validations depending on user
# context.
CREDIT_SOFT_MAX = 55
# Students can't take over this amount of credits without special authorization.
CREDIT_HARD_MAX = 65

# Used to mean unfeasability.
INFINITY = 10**9


@dataclass
class CourseInstance:
    """
    An instance of a course within a plan.
    Has a position (semester, index) within the plan.
    """

    code: str
    sem: int
    index: int


def _get_equivalents(courseinfo: CourseInfo, course: PseudoCourse) -> list[str]:
    """
    Get all of the course codes that are equivalent to `course`, including itself.
    """
    info = courseinfo.try_course(course.code)
    if info is None:
        return []
    equiv_codes = info.banner_equivs.copy()
    equiv_codes.append(course.code)
    return equiv_codes


class ValidationContext:
    """
    Pre-processing of a validatable plan, created once and used to validate the course
    rules for all classes.
    """

    # NOTE: When changing the fields of `ValidationContext`, you have to make sure that
    # `append_semester`, `append_course` and `pop_course` keep the fields properly in
    # sync.

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
    user_ctx: StudentInfo | None
    # On which semester to start validating requirements and other associated
    # validations.
    # Should be the first semester that has not yet been taken (ie. the semester after
    # the current one).
    start_validation_from: int

    def __init__(
        self,
        courseinfo: CourseInfo,
        plan: ValidatablePlan,
        user_ctx: StudentInfo | None,
    ) -> None:
        # Map from coursecode to course instance
        self.by_code = {}
        for sem_i, sem in enumerate(plan.classes):
            for i, course in enumerate(sem):
                # Map the equivalent courses to this course instance
                course_inst = CourseInstance(code=course.code, sem=sem_i, index=i)
                for code in _get_equivalents(courseinfo, course):
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

    def append_semester(self):
        """
        Add an empty semester to the plan, updating the validation context.
        """
        self.class_ids.append([])
        self.approved_credits.append(self.approved_credits[-1])
        self.plan.classes.append([])

    def append_course(self, course: PseudoCourse):
        """
        Add a course at the last semester.
        """
        assert len(self.plan.classes) > 0

        # Get positioning indices
        rep_idx = 0
        for sem in self.plan.classes:
            for c in sem:
                if c.code == course.code:
                    rep_idx += 1
        sem_idx = len(self.plan.classes) - 1
        order_idx = len(self.plan.classes[-1])

        # Actually add course
        self.plan.classes[-1].append(course)
        self.class_ids[-1].append(ClassId(code=course.code, instance=rep_idx))
        self.approved_credits[-1] += self.courseinfo.get_credits(course) or 0

        # Update passed codes
        inst = CourseInstance(code=course.code, sem=sem_idx, index=order_idx)
        for code in _get_equivalents(self.courseinfo, course):
            if code not in self.by_code:
                self.by_code[code] = inst

    def pop_course(self):
        """
        Pop the last course of the last semester.
        (There must be at least 1 course in the last semester)
        """
        assert len(self.plan.classes) > 0
        assert len(self.plan.classes[-1]) > 0

        # Get the position of the course to remove
        sem_idx = len(self.plan.classes) - 1
        order_idx = len(self.plan.classes[-1]) - 1

        # Remove course
        course = self.plan.classes[-1].pop()
        self.class_ids[-1].pop()
        self.approved_credits[-1] -= self.courseinfo.get_credits(course) or 0

        # Update passed codes
        for code in _get_equivalents(self.courseinfo, course):
            inst = self.by_code[code]
            if inst.sem == sem_idx and inst.index == order_idx:
                # This is the earliest course compatible with this code
                # Because this is the last course, once this course is removed there can
                # be no other compatible course
                del self.by_code[code]

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
            out.add(AmbiguousCourseWarn(associated_to=ambiguous))

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
                        if not self.courseinfo.is_available(course.code):
                            # This course is plain unavailable
                            unavailable.append(self.class_ids[sem_i][i])
                        elif (
                            not info.semestrality[sem_i % 2]
                            and info.semestrality[(sem_i + 1) % 2]
                        ):
                            # This course is only available on the other semester
                            only_on_sem[(sem_i + 1) % 2].append(
                                self.class_ids[sem_i][i],
                            )
        if unavailable:
            out.add(UnavailableCourseWarn(associated_to=unavailable))
        for k in range(2):
            if only_on_sem[k]:
                out.add(
                    SemestralityWarn(associated_to=only_on_sem[k], only_available_on=k),
                )

    def validate_max_credits(self, out: ValidationResult):
        """
        Validate that there are no semester with an excess of credits.
        """

        for sem_i in range(self.start_validation_from, len(self.plan.classes)):
            sem_credits = 0
            for course in self.plan.classes[sem_i]:
                sem_credits += self.courseinfo.get_credits(course) or 0
            if sem_credits > CREDIT_HARD_MAX:
                out.add(
                    SemesterCreditsDiag(
                        is_err=True,
                        associated_to=[sem_i],
                        credit_limit=CREDIT_HARD_MAX,
                        actual=sem_credits,
                    ),
                )
            elif sem_credits > CREDIT_SOFT_MAX:
                out.add(
                    SemesterCreditsDiag(
                        is_err=False,
                        associated_to=[sem_i],
                        credit_limit=CREDIT_SOFT_MAX,
                        actual=sem_credits,
                    ),
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
                        out,
                        CourseInstance(code, sem_i, i),
                        info.deps,
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
        self,
        out: ValidationResult,
        inst: CourseInstance,
        expr: "Expr",
    ):
        """
        Validate the requirements for the course `inst`.
        """
        if is_satisfied(self, inst, expr):
            return
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
                or isinstance(atom, ReqSchool | ReqProgram | ReqCareer)
                or (
                    isinstance(atom, ReqCourse)
                    and not is_course_indirectly_available(self.courseinfo, atom.code)
                ),
            ),
        )
        # Stage 2: allow unavailable courses
        if isinstance(missing, Const):
            missing = simplify(
                set_atoms_in_stone_if(
                    self,
                    inst,
                    expr,
                    lambda atom, sat: sat
                    or isinstance(atom, ReqSchool | ReqProgram | ReqCareer),
                ),
            )
        # Stage 3: allow changing everything
        if isinstance(missing, Const):
            # Only set atoms in stone if they are satisfied (ie. leave all unsatisfied
            # requirements as free variables)
            missing = simplify(
                set_atoms_in_stone_if(self, inst, expr, lambda atom, sat: sat),
            )
        # Map missing courses to their newest equivalent versions
        missing_equivalents = simplify(map_atoms(missing, self.map_to_equivalent))
        # Figure out if we can push this course back and solve the missing requirements
        push_back = find_minimum_semester(self, missing)
        # Figure out if we can pull any dependencies forward
        pull_forward: dict[str, int] = {}
        self.find_pull_forwards(inst, pull_forward, missing)
        pull_forward = {
            code: sem
            for code, sem in pull_forward.items()
            if sem >= self.start_validation_from
        }
        # Find absent courses
        absent: dict[str, int] = {}
        self.find_absent(inst, absent, missing_equivalents)
        # Show this expression
        out.add(
            CourseRequirementErr(
                associated_to=[self.class_ids[inst.sem][inst.index]],
                missing=missing,
                modernized_missing=missing_equivalents,
                push_back=None if push_back == INFINITY else push_back,
                pull_forward=pull_forward,
                add_absent=absent,
            ),
        )

    def check_dependencies_for(self, sem: int, idx: int) -> bool:
        """
        Very basic yes/no checker for the dependencies of course at the given index.
        Return "yes" if the course is not a concrete course or is not known.
        """
        course = self.plan.classes[sem][idx]
        info = self.courseinfo.try_course(course.code)
        if info is None:
            return True
        cl = CourseInstance(course.code, sem, idx)
        return is_satisfied(self, cl, info.deps)

    def find_pull_forwards(
        self,
        inst: CourseInstance,
        pull_forward: dict[str, int],
        expr: Expr,
    ):
        if isinstance(expr, Operator):
            for child in expr.children:
                self.find_pull_forwards(inst, pull_forward, child)
        if isinstance(expr, ReqCourse) and expr.code in self.by_code:
            req = self.by_code[expr.code]
            req_sem = inst.sem - (0 if expr.coreq else 1)
            if req.sem > req_sem:
                pull_forward[req.code] = min(
                    pull_forward.get(req.code, INFINITY),
                    req_sem,
                )

    def find_absent(self, inst: CourseInstance, absent: dict[str, int], expr: Expr):
        if isinstance(expr, Operator):
            for child in expr.children:
                self.find_absent(inst, absent, child)
        if isinstance(expr, ReqCourse) and expr.code not in self.by_code:
            add_on_sem = max(
                inst.sem - (0 if expr.coreq else 1),
                self.start_validation_from,
            )
            absent[expr.code] = min(absent.get(expr.code, INFINITY), add_on_sem)

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
        for child in expr.children:
            value = is_satisfied(ctx, cl, child)
            if value != expr.neutral:
                return value
        return expr.neutral
    if isinstance(expr, MinCredits):
        return ctx.approved_credits[cl.sem] >= expr.min_credits
    if isinstance(expr, ReqLevel):
        # TODO: Is this a `>=` relationship or actually an `=` relationship?
        return (ctx.plan.level == expr.level) == expr.equal
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
        return (req_cl.sem <= cl.sem) if expr.coreq else (req_cl.sem < cl.sem)
    return expr.value


def find_minimum_semester(ctx: ValidationContext, expr: Expr) -> int:
    """
    Given a dependency expression, find the minimum semester where the class would have
    to be in order to be satisfied.
    Can be used to determine how much to "push back" courses.
    """
    if isinstance(expr, And):
        # The course must be as late as the most late subrequirement
        sem = -INFINITY
        for child in expr.children:
            sem = max(sem, find_minimum_semester(ctx, child))
        return sem
    if isinstance(expr, Or):
        # The course must only be as late as the least late subrequirement
        sem = INFINITY
        for child in expr.children:
            sem = min(sem, find_minimum_semester(ctx, child))
        return sem
    if isinstance(expr, MinCredits):
        # The course needs to be at least as far back as to have approved n credits
        for sem, creds in enumerate(ctx.approved_credits):
            if creds >= expr.min_credits:
                return sem
        return INFINITY
    if isinstance(expr, ReqLevel | ReqSchool | ReqProgram | ReqCareer):
        # Can't fix these just by changing the course semester
        return INFINITY
    if isinstance(expr, ReqCourse):
        # We must be as late as this semester (or this semester + 1)
        if expr.code not in ctx.by_code:
            return INFINITY
        return ctx.by_code[expr.code].sem + (0 if expr.coreq else 1)
    # Depending on the constant value this is feasible or unfeasible
    return -INFINITY if expr.value else INFINITY


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

    def mapping(atom: Atom) -> Atom:
        # Maybe replace this atom by its constant truth value
        truth = is_satisfied(ctx, cl, atom)
        if should_set_in_stone(atom, truth):
            # Fold this atom into its constant truth value
            return Const(value=truth)
        return atom

    return map_atoms(expr, mapping)


def is_course_indirectly_available(courseinfo: CourseInfo, code: str):
    """
    Check if a course is available OR there is an available equivalent.
    """
    if courseinfo.is_available(code):
        return True
    info = courseinfo.try_course(code)
    if info is None:
        return False
    return courseinfo.is_available(info.canonical_equiv)
