from collections import OrderedDict, defaultdict
from collections.abc import Iterable

from .. import sync
from ..sync import get_curriculum
from ..user.auth import UserKey
from .course import ConcreteId, EquivalenceId, pseudocourse_with_credits
from .courseinfo import CourseInfo, course_info
from .plan import (
    PseudoCourse,
    ValidatablePlan,
)
from .validation.courses.logic import And, Expr, Or, ReqCourse
from .validation.courses.validate import ValidationContext
from .validation.curriculum.solve import (
    FilledCourse,
    LayerCourse,
    SolvedCurriculum,
    solve_curriculum,
)
from .validation.curriculum.tree import (
    LATEST_CYEAR,
    Curriculum,
    CurriculumSpec,
    Cyear,
)

RECOMMENDED_CREDITS_PER_SEMESTER = 50


def _count_credits(courseinfo: CourseInfo, sem: Iterable[PseudoCourse]) -> int:
    return sum(courseinfo.get_credits(course) or 0 for course in sem)


def _extract_active_fillers(
    g: SolvedCurriculum,
) -> OrderedDict[int, PseudoCourse]:
    """
    Extract course recommendations from a solved curriculum.
    If missing credits are found, `to_pass` is filled with the corresponding filler
    courses from the `fill_with` fields.
    """
    # Make sure to only add courses once
    added: defaultdict[str, set[int]] = defaultdict(set)
    to_pass: list[tuple[LayerCourse, FilledCourse]] = []
    for layer in g.layers.values():
        for code, courses in layer.courses.items():
            for rep_idx, course in courses.items():
                if isinstance(course.origin, FilledCourse):
                    # Check whether we should add this course
                    if course.active_edge is None:
                        continue
                    if rep_idx in added[code]:
                        continue
                    added[code].add(rep_idx)

                    # Add this course
                    to_pass.append((course, course.origin))

    # Sort courses by order
    to_pass.sort(key=lambda c: c[1].fill_with.order)

    # Flatten into plain pseudocourse ids, taking active credits into account
    i = 0
    flattened: OrderedDict[int, PseudoCourse] = OrderedDict()
    for info, course in to_pass:
        flattened[i] = pseudocourse_with_credits(
            course.fill_with.course,
            info.active_flow,
        )
        i += 1
    return flattened


def _compute_courses_to_pass(
    courseinfo: CourseInfo,
    curriculum: Curriculum,
    passed_classes: list[list[PseudoCourse]],
) -> OrderedDict[int, PseudoCourse]:
    """
    Given a curriculum with recommendations, and a plan that is considered as "passed",
    add classes after the last semester to match the recommended plan.
    """

    # Determine which curriculum blocks have not been passed yet
    g = solve_curriculum(courseinfo, curriculum, passed_classes)

    # Extract recommended courses from solved plan
    return _extract_active_fillers(g)


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
        student = await sync.get_student_data(user)
        cyear = Cyear.from_str(student.info.cyear)
        if cyear is None:
            # Just plow forward, after all the validation endpoint will generate an
            # error about the mismatched cyear
            cyear = LATEST_CYEAR
        classes = student.passed_courses
        curriculum = CurriculumSpec(
            cyear=cyear,
            major=student.info.reported_major,
            minor=student.info.reported_minor,
            title=student.info.reported_title,
        )
    return ValidatablePlan(
        version="0.0.1",
        classes=classes,
        level="Pregrado",
        school="Ingenieria",
        program=None,
        career="Ingenieria",
        curriculum=curriculum,
    )


async def generate_recommended_plan(passed: ValidatablePlan):
    """
    Take a base plan that the user has already passed, and recommend a plan that should
    lead to the user getting the title in whatever major-minor-career they chose.
    """
    from time import monotonic as t

    t0 = t()
    courseinfo = await course_info()
    curriculum = await get_curriculum(passed.curriculum)
    t1 = t()

    # Flat list of all curriculum courses left to pass
    courses_to_pass = _compute_courses_to_pass(courseinfo, curriculum, passed.classes)
    t2 = t()

    plan_ctx = ValidationContext(courseinfo, passed.copy(deep=True), user_ctx=None)
    plan_ctx.append_semester()

    # Precompute corequirements for courses
    coreq_components = _find_mutual_coreqs(courseinfo, courses_to_pass)
    t21 = t()

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
        # However, we do not want to enter an infinite loop if nothing can be added, so
        # only do this if we cannot add courses for 2 empty semesters
        if (
            len(plan_ctx.plan.classes) >= 2
            and not plan_ctx.plan.classes[-1]
            and not plan_ctx.plan.classes[-2]
        ):
            # Stuck :(
            break

        # Maybe some requirements are not met, maybe the semestrality is wrong, maybe
        # we reached the credit limit for this semester
        # Anyway, if we are stuck let's try adding a new semester and see if it helps
        plan_ctx.append_semester()

    # Unwrap plan
    plan = plan_ctx.plan

    # Remove empty semesters at the end (if any)
    while plan.classes and not plan.classes[-1]:
        plan.classes.pop()

    if courses_to_pass:
        print(f"WARNING: could not add courses {list(courses_to_pass.values())}")
        plan.classes.append(list(courses_to_pass.values()))

    t3 = t()

    def p(t: float):
        return f"{round(t*1000, 2)}ms"

    print(f"generation: {p(t3-t0)}")
    print(f"  resource lookup: {p(t1-t0)}")
    print(f"  solve: {p(t2-t1)}")
    print(f"  coreq: {p(t21-t2)}")
    print(f"  insert: {p(t3-t21)}")

    return plan
