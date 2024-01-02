import logging
import time
from collections import OrderedDict, defaultdict
from collections.abc import Iterable
from types import TracebackType

from app import sync
from app.plan.course import (
    ConcreteId,
    EquivalenceId,
    pseudocourse_with_credits,
)
from app.plan.courseinfo import CourseDetails, CourseInfo
from app.plan.plan import (
    CURRENT_PLAN_VERSION,
    PseudoCourse,
    ValidatablePlan,
)
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
    create_op,
    hash_expr,
    map_atoms,
)
from app.plan.validation.courses.simplify import as_dnf, simplify
from app.plan.validation.courses.validate import CourseInstance, ValidationContext
from app.plan.validation.curriculum.solve import (
    SolvedCurriculum,
    solve_curriculum,
)
from app.plan.validation.curriculum.tree import (
    LATEST_CYEAR,
    Curriculum,
    CurriculumSpec,
    FillerCourse,
    cyear_from_str,
)
from app.sync import get_curriculum
from app.sync.database import course_info
from app.user.auth import UserKey

log = logging.getLogger("plan-gen")

RECOMMENDED_CREDITS_PER_SEMESTER = 50


def _count_credits(courseinfo: CourseInfo, sem: Iterable[PseudoCourse]) -> int:
    return sum(courseinfo.get_credits(course) or 0 for course in sem)


SUPERBLOCK_COLOR_ORDER_TABLE: dict[str, int] = {
    "PlanComun": 0,
    "Major": 1,
    "Minor": 2,
    "Titulo": 3,
    "FormacionGeneral": 4,
}


def _get_course_color_order(
    g: SolvedCurriculum,
    rep_counter: defaultdict[str, int],
    course_code: str,
) -> int:
    """
    Get the course "priority", which depends on the "color" of the course.
    The color of the course is basically what superblock it counts towards.
    Courses with lower priority number go before courses with a higher priority number.
    """
    rep_idx = rep_counter[course_code]
    rep_counter[course_code] += 1
    superblock = ""
    if course_code in g.superblocks and rep_idx < len(g.superblocks[course_code]):
        superblock = g.superblocks[course_code][rep_idx]
    return SUPERBLOCK_COLOR_ORDER_TABLE.get(superblock, 1000)


def _extract_active_fillers(
    g: SolvedCurriculum,
) -> OrderedDict[int, PseudoCourse]:
    """
    Extract course recommendations from a solved curriculum.
    If missing credits are found, `to_pass` is filled with the corresponding filler
    courses from the `fill_with` fields.
    """
    to_pass: list[tuple[int, PseudoCourse]] = []
    for usable in g.usable.values():
        for inst in usable.instances:
            if inst.filler is None or inst.flow == 0:
                continue

            # Add this course
            to_pass.append(
                (
                    inst.filler.order,
                    pseudocourse_with_credits(inst.filler.course, inst.flow),
                ),
            )

    # Sort courses by order
    to_pass.sort(key=lambda pair: pair[0])

    # Remove order information
    return OrderedDict({i: course for i, (_order, course) in enumerate(to_pass)})


def _is_satisfiable(plan: ValidatablePlan, ready: set[str], expr: Expr) -> bool:
    """
    Check if the requirement is satisfiable given the plan and a set of passed codes.
    Similar to `_is_satisfied`, but it relaxes some checks.
    May generate false positives, but never false negatives.
    """
    if isinstance(expr, Operator):
        for child in expr.children:
            value = _is_satisfiable(plan, ready, child)
            if value != expr.neutral:
                return value
        return expr.neutral
    if isinstance(expr, MinCredits):
        # This check is relaxed:
        # Assume that we can fulfill the credit requirements
        return True
    if isinstance(expr, ReqCourse):
        # This check is relaxed:
        # Does not check course semesters, and it assumes that there are no impossible
        # cycles
        return expr.code in ready
    if isinstance(expr, ReqLevel):
        return (plan.level == expr.level) == expr.equal
    if isinstance(expr, ReqSchool):
        return (plan.school == expr.school) == expr.equal
    if isinstance(expr, ReqProgram):
        return (plan.program == expr.program) == expr.equal
    if isinstance(expr, ReqCareer):
        return (plan.career == expr.career) == expr.equal
    return expr.value


class Collapser:
    atom_counts: dict[bytes, int]
    expands_to: dict[bytes, list[Atom]]
    collapsed: Expr

    def __init__(self, expr: Expr) -> None:
        self.atom_counts = {}
        self._count_atoms(expr)
        self.expands_to = {}
        self.collapsed = self._collapse(expr)

    def _count_atoms(self, expr: Expr):
        if isinstance(expr, Operator):
            for child in expr.children:
                self._count_atoms(child)
        else:
            self.atom_counts[hash_expr(expr)] = (
                self.atom_counts.get(hash_expr(expr), 0) + 1
            )

    def _collapse(self, expr: Expr) -> Expr:
        if isinstance(expr, Operator):
            new_children: list[Expr] = []
            representative: Atom | None = None
            for child in expr.children:
                child = self._collapse(child)
                if (
                    isinstance(child, Atom)
                    and self.atom_counts.get(hash_expr(child), 1) == 1
                ):
                    if representative is None:
                        if isinstance(expr, And):
                            representative = ReqCourse(
                                code=str(len(self.expands_to)),
                                coreq=False,
                            )
                            self.expands_to[hash_expr(representative)] = self.expand(
                                child,
                            )
                        else:
                            representative = child
                    else:
                        if isinstance(expr, And):
                            self.expands_to[hash_expr(representative)].extend(
                                self.expand(child),
                            )
                        else:
                            if self._weight_of(child) < self._weight_of(representative):
                                representative = child
                else:
                    new_children.append(child)
            if representative is not None:
                new_children.append(representative)
            if len(new_children) == 1:
                return new_children[0]
            else:
                return create_op(expr.neutral, tuple(new_children))
        else:
            return expr

    def _weight_of(self, atom: Atom) -> int:
        if hash_expr(atom) in self.expands_to:
            return len(self.expands_to[hash_expr(atom)])
        else:
            return 1

    def expand(
        self,
        atom: Atom,
    ) -> list[Atom]:
        if hash_expr(atom) in self.expands_to:
            return self.expands_to[hash_expr(atom)]
        else:
            return [atom]


def _find_hidden_requirements(
    courseinfo: CourseInfo,
    passed: ValidatablePlan,
    courses_to_pass: OrderedDict[int, PseudoCourse],
) -> list[str]:
    """
    Take the list of courses to pass and compute which necessary requirements are
    missing.
    Computes all possible ways to complete the hidden requirements, and returns one of
    the shortest (arbitrarily).
    """

    b = Benchmark("hidden requirements")

    # Compute a big list of taken and to-be-passed courses
    with b.section("collect courses"):
        all_courses: list[CourseDetails] = []
        for sem in passed.classes:
            for course in sem:
                info = courseinfo.try_course(course.code)
                if info is not None:
                    all_courses.append(info)
        for course in courses_to_pass.values():
            info = courseinfo.try_course(course.code)
            if info is not None:
                all_courses.append(info)

        # Compute which courses are considered taken
        ready: set[str] = {course.code for course in all_courses}

    # Find courses with missing requirements, and add them here
    with b.section("collect requirements"):
        missing: list[Expr] = []
        for course in all_courses:
            if _is_satisfiable(passed, ready, course.deps):
                continue

            # Something missing!
            def map(atom: Atom) -> Atom:
                if _is_satisfiable(passed, ready, atom):
                    # Already satisfiable, don't worry about it
                    return Const(value=True)
                if isinstance(atom, ReqCourse):
                    # We *could* satisfy this atom by adding a course
                    # Ignore corequirements for simplicity
                    return ReqCourse(code=atom.code, coreq=False)
                # Not satisfiable by adding a course
                # Consider this impossible
                return Const(value=False)

            missing.append(map_atoms(course.deps, map))

        # Good case: there is nothing missing
        # Exit early to avoid some computations
        if not missing:
            return []

    # Apply some domain-specific heuristics
    # In particular, recognize courses that are equivalent, and consider them as 1
    # pseudo-course
    with b.section("simplify"):
        missing_expr = And(children=tuple(missing))
        missing_expr = simplify(missing_expr)

    with b.section("collapse"):
        collapser = Collapser(missing_expr)
        missing_expr = collapser.collapsed

    # Normalize the resulting expression to DNF:
    # (IIC1000 y IIC1001) o (IIC1000 y IIC1002) o (IIC2000 y IIC1002)
    # (ie. an OR of ANDs)
    with b.section("dnfize"):
        missing_dnf = as_dnf(missing_expr)

    with b.section("expand"):
        to_fill = min(
            (
                [
                    expanded_atom.code
                    for pseudoatom in clause.children
                    for expanded_atom in collapser.expand(pseudoatom)
                    if isinstance(expanded_atom, ReqCourse)
                ]
                for clause in missing_dnf.children
            ),
            key=lambda opt: len(opt),
        )

    with b.section("debug printing"):
        print(f"consider-as-passed: {to_fill}")

    return to_fill


def _reselect_equivs(
    courseinfo: CourseInfo,
    curriculum: Curriculum,
    reference: ValidatablePlan,
):
    """
    Update the filler equivalences in `curriculum` to match choices in `reference`.

    Context: When the user changes their curriculum spec (eg. changes major), we'd like
    to keep as many choices that the user took as possible.
    However, different curriculums may be very different, so it's hard to carry
    information over to the new curriculum.
    One thing that is relatively easy to carry over are equivalence choices: the
    concrete course chosen for an equivalence.
    """

    # Collect equivalence choices by equivalence name
    by_name: defaultdict[str, list[ConcreteId]] = defaultdict(list)
    for ref_sem in reference.classes:
        for ref_course in ref_sem:
            if (
                isinstance(ref_course, ConcreteId)
                and ref_course.equivalence is not None
            ):
                ref_equiv = ref_course.equivalence
                equiv_info = courseinfo.try_equiv(ref_equiv.code)
                if equiv_info is not None and len(equiv_info.courses) > 1:
                    by_name[equiv_info.name].append(ref_course)

    # Re-select filler equivalences in courses_to_pass if they match reference choices
    extra_fillers: defaultdict[str, list[FillerCourse]] = defaultdict(list)
    for fillers in curriculum.fillers.values():
        for filler in fillers:
            equiv = filler.course
            if isinstance(equiv, ConcreteId):
                equiv = equiv.equivalence
            if equiv is None:
                continue

            equiv_info = courseinfo.try_equiv(equiv.code)
            if equiv_info is None or equiv_info.name not in by_name:
                continue
            for ref_choice in by_name[equiv_info.name]:
                if (
                    ref_choice.code in equiv_info.courses
                    and ref_choice.code != filler.course.code
                ):
                    extra_fillers[ref_choice.code].append(
                        FillerCourse(
                            course=ref_choice.copy(update={"equivalence": equiv}),
                            order=filler.order,
                            cost_offset=filler.cost_offset - 1,
                        ),
                    )
                    break

    # Add extra fillers at the start of the lists
    for code, extra in extra_fillers.items():
        if code in curriculum.fillers:
            extra.extend(curriculum.fillers[code])
        curriculum.fillers[code] = extra


def _compute_courses_to_pass(
    courseinfo: CourseInfo,
    g: SolvedCurriculum,
    passed: ValidatablePlan,
) -> tuple[OrderedDict[int, PseudoCourse], list[str]]:
    """
    Given a curriculum with recommendations, and a plan that is considered as "passed",
    add classes after the last semester to match the recommended plan.
    """

    # Extract recommended courses from solved plan
    courses_to_pass = _extract_active_fillers(g)

    # Find out which requirements are missing from the plan
    extra_reqs = _find_hidden_requirements(courseinfo, passed, courses_to_pass)

    # TODO: Automatically place the extra courses
    # This has at least 3 problems:
    # 1. It becomes very obvious that the plan generation algorithm is not optimal in
    #   amount-of-semesters.
    # 2. It makes decisions for the user, who should be at least notified that decisions
    #   were made for them.
    # 3. Some of these courses might be part of the curriculum, but "hidden" within
    #   equivalences.
    #   Automatically adding the courses has the effect of "duplicating" these courses:
    #   once in an equivalence and then again as a concrete course that serves no
    #   purpose.
    #   This could be taken into account, for example by first finding hidden
    #   requirements and then solving the curriculum, but that would have the effect of
    #   automatically choosing equivalences, worsening problem #2.
    consider_as_passed = extra_reqs

    return courses_to_pass, consider_as_passed


def _extract_corequirements(out: set[str], expr: Expr):
    if isinstance(expr, ReqCourse) and expr.coreq:
        out.add(expr.code)
    elif isinstance(expr, And | Or):
        for child in expr.children:
            _extract_corequirements(out, child)


def _get_course_corequirements(
    courseinfo: CourseInfo,
    course: PseudoCourse,
) -> set[str]:
    out: set[str] = set()
    if isinstance(course, EquivalenceId):
        return out
    info = courseinfo.try_course(course.code)
    if info is not None:
        _extract_corequirements(out, info.deps)
    return out


def _find_mutual_coreqs(
    courseinfo: CourseInfo,
    courses_to_pass: OrderedDict[int, PseudoCourse],
) -> list[list[int]]:
    """
    For each course, find which other courses in the list are mutual corequirements.
    A course is considered a mutual corequirement of itself, always.
    Wonky stuff may happen if there are duplicated concrete courses in the
    `courses_to_pass` list.
    Equivalences are ignored entirely, only concrete courses are taken into account.
    """

    # First, create a mapping from course code to courses in `courses_to_pass`
    code_to_idx: dict[str, int] = {}
    for idx, course in courses_to_pass.items():
        if isinstance(course, ConcreteId):
            code_to_idx[course.code] = idx

    # Now, get the raw list of corequirements for each course to pass
    coreqs_of: list[set[str]] = []
    for courseid in courses_to_pass.values():
        coreqs_of.append(
            _get_course_corequirements(
                courseinfo,
                courseid,
            ),
        )

    # For each course, filter the corequirements which are mutual
    mutual_coreqs: list[list[int]] = []
    for idx, course in courses_to_pass.items():
        # I am always my own mutual corequirement
        mutual = [idx]
        # Check each corequirement for mutuality
        for coreq_code in coreqs_of[idx]:
            if coreq_code in code_to_idx:
                # Ok, this corequirement exists in the `courses_to_pass`
                coreq_idx = code_to_idx[coreq_code]
                if course.code in coreqs_of[coreq_idx]:
                    # I am a corequirement of my corequirement, so it's mutual
                    mutual.append(coreq_idx)
        mutual_coreqs.append(mutual)

    return mutual_coreqs


def _try_add_course_group(
    courseinfo: CourseInfo,
    plan_ctx: ValidationContext,
    courses_to_pass: OrderedDict[int, PseudoCourse],
    course_group: list[int],
) -> bool:
    """
    Attempt to add a group of courses to the last semester of the given plan.
    Fails if they cannot be added.
    Assumes all courses in the group are not present in the given plan.
    Returns `True` if the courses could be added.
    """

    # Bail if the semestrality is wrong for any course (but it could be right in
    # another semester)
    sem_i = len(plan_ctx.plan.classes) - 1
    for idx in course_group:
        if idx not in courses_to_pass:
            continue
        course = courses_to_pass[idx]
        info = courseinfo.try_course(course.code)
        if info is None:
            continue
        if not info.semestrality[sem_i % 2] and info.semestrality[(sem_i + 1) % 2]:
            return False

    # Determine total credits of this group
    group_credits = _count_credits(
        courseinfo,
        (courses_to_pass[idx] for idx in course_group if idx in courses_to_pass),
    )

    # Bail if there is not enough space in this semester
    current_credits = plan_ctx.approved_credits[-1]
    if len(plan_ctx.approved_credits) >= 2:
        current_credits -= plan_ctx.approved_credits[-2]
    if current_credits + group_credits > RECOMMENDED_CREDITS_PER_SEMESTER:
        return False

    # Temporarily add to plan
    added_n = 0
    for idx in course_group:
        if idx not in courses_to_pass:
            continue
        plan_ctx.append_course(courses_to_pass[idx])
        added_n += 1

    # Check the dependencies for each course
    i = 0
    for idx in course_group:
        if idx not in courses_to_pass:
            continue
        course = courses_to_pass[idx]
        if not plan_ctx.check_dependencies_for(
            sem_i,
            len(plan_ctx.plan.classes[-1]) - added_n + i,
        ):
            # Requirements are not met
            # Undo changes and cancel
            for _ in range(added_n):
                plan_ctx.pop_course()
            return False
        i += 1

    # Added course successfully
    # Remove added courses from `courses_to_pass`
    for idx in course_group:
        if idx in courses_to_pass:
            del courses_to_pass[idx]

    return True


async def generate_empty_plan(user: UserKey | None = None) -> ValidatablePlan:
    """
    Generate an empty plan with optional user context.
    If no user context is available, uses the latest curriculum version.

    All plans are born from this function (or deserialized from plans that were born
    from this function, except for manually crafted plans).
    """
    classes: list[list[PseudoCourse]]
    curriculum: CurriculumSpec
    if user is None:
        classes = []
        curriculum = CurriculumSpec(
            cyear=LATEST_CYEAR,
            major=None,
            minor=None,
            title=None,
        )
    else:
        student = await sync.get_student_info(user)
        cyear = cyear_from_str(student.cyear)
        if cyear is None:
            # Just plow forward, after all the validation endpoint will generate an
            # error about the mismatched cyear
            cyear = LATEST_CYEAR
        classes = student.passed_courses
        curriculum = CurriculumSpec(
            cyear=cyear,
            major=student.reported_major,
            minor=student.reported_minor,
            title=student.reported_title,
        )
    return ValidatablePlan(
        version=CURRENT_PLAN_VERSION,
        classes=classes,
        level="Pregrado",
        school="Ingenieria",
        program=None,
        career="Ingenieria",
        curriculum=curriculum,
    )


class Benchmark:
    start: float
    name: str

    def __init__(self, bigname: str) -> None:
        log.debug("%s:", bigname)
        self.name = "?"
        self.start = 0

    def section(self, name: str) -> "Benchmark":
        self.name = name
        return self

    def __enter__(self) -> None:
        self.start = time.monotonic()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_trace: TracebackType | None,
    ) -> None:
        end = time.monotonic()
        t = end - self.start
        log.debug("  %s: %sms", self.name, round(1000 * t, 2))


async def generate_recommended_plan(
    passed: ValidatablePlan,
    reference: ValidatablePlan | None = None,
):
    """
    Take a base plan that the user has already passed, and recommend a plan that should
    lead to the user getting the title in whatever major-minor-career they chose.

    NOTE: This function modifies `passed`.
    """
    b = Benchmark("plan generation")

    with b.section("resource lookup"):
        courseinfo = await course_info()
        curriculum = await get_curriculum(passed.curriculum)

    # Re-select courses from equivalences using reference plan
    with b.section("ref reselect"):
        if reference is not None:
            _reselect_equivs(courseinfo, curriculum, reference)

    # Solve the curriculum to determine which courses have not been passed yet (and need
    # to be passed)
    with b.section("solve"):
        g = solve_curriculum(
            courseinfo,
            passed.curriculum,
            curriculum,
            passed.classes,
            len(passed.classes),
        )

    # Flat list of all curriculum courses left to pass
    with b.section("courses to pass"):
        courses_to_pass, ignore_reqs = _compute_courses_to_pass(
            courseinfo,
            g,
            passed,
        )

    plan_ctx = ValidationContext(courseinfo, passed.copy(deep=True), user_ctx=None)
    for ignore in ignore_reqs:
        plan_ctx.by_code[ignore] = CourseInstance(code=ignore, sem=-(10**9), index=0)
    plan_ctx.append_semester()

    # Precompute corequirements for courses
    with b.section("coreq"):
        coreq_components = _find_mutual_coreqs(courseinfo, courses_to_pass)

    with b.section("placement"):
        while courses_to_pass:
            # Attempt to add a single course at the end of the last semester

            # Go in order, attempting to add each course to the semester
            added_course = False
            for idx in courses_to_pass:
                course_group = coreq_components[idx]

                could_add = _try_add_course_group(
                    courseinfo,
                    plan_ctx,
                    courses_to_pass,
                    course_group,
                )
                if could_add:
                    # Successfully added a course, finish
                    added_course = True
                    break

            if added_course:
                # Made some progress!
                # Continue adding courses
                continue

            # We could not add any course, try adding another semester
            # However, we do not want to enter an infinite loop if nothing can be added,
            # so only do this if we cannot add courses for 2 empty semesters
            if (
                len(plan_ctx.plan.classes) >= 2
                and not plan_ctx.plan.classes[-1]
                and not plan_ctx.plan.classes[-2]
            ):
                # Stuck :(
                break

            # Maybe some requirements are not met, maybe the semestrality is wrong,
            # maybe we reached the credit limit for this semester
            # Anyway, if we are stuck let's try adding a new semester and see if it
            # helps
            plan_ctx.append_semester()

        # Unwrap plan
        plan = plan_ctx.plan

        # Remove empty semesters at the end (if any)
        while plan.classes and not plan.classes[-1]:
            plan.classes.pop()

        # If any courses simply could not be added, add them now
        # TODO: Do something about courses with missing requirements
        if courses_to_pass:
            print(f"WARNING: could not add courses {list(courses_to_pass.values())}")
            plan.classes.append(list(courses_to_pass.values()))

    # Assign blocks to courses based on the current solution
    with b.section("recolor"):
        g.execute_recolors(plan.classes)

    # Order courses by their color (ie. superblock assignment)
    with b.section("reorder"):
        repetition_counter: defaultdict[str, int] = defaultdict(lambda: 0)
        plan.classes = [
            [
                c
                for _order, c in sorted(
                    (
                        (_get_course_color_order(g, repetition_counter, c.code), c)
                        for c in sem
                    ),
                    key=lambda pair: pair[0],
                )
            ]
            for sem in plan.classes
        ]

    return plan
