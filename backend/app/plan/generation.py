from collections import defaultdict

from .. import sync
from ..sync import get_curriculum
from ..user.auth import UserKey
from .course import ConcreteId, EquivalenceId
from .courseinfo import CourseInfo, course_info
from .plan import (
    Level,
    PseudoCourse,
    ValidatablePlan,
)
from .validation.courses.logic import And, Expr, Or, ReqCourse
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
from .validation.validate import quick_validate_dependencies

RECOMMENDED_CREDITS_PER_SEMESTER = 50


def _extract_active_fillers(
    g: SolvedCurriculum,
) -> list[PseudoCourse]:
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
    flattened: list[PseudoCourse] = []
    for info, course in to_pass:
        cid = course.fill_with.course
        equiv = cid if isinstance(cid, EquivalenceId) else cid.equivalence
        if equiv is not None:
            equiv = EquivalenceId(code=equiv.code, credits=info.active_flow)
            if isinstance(cid, EquivalenceId):
                cid = equiv
            else:
                cid = ConcreteId(code=cid.code, equivalence=equiv)
        flattened.append(cid)
    return flattened


def _compute_courses_to_pass(
    courseinfo: CourseInfo,
    curriculum: Curriculum,
    passed_classes: list[list[PseudoCourse]],
) -> list[PseudoCourse]:
    """
    Given a curriculum with recommendations, and a plan that is considered as "passed",
    add classes after the last semester to match the recommended plan.
    """

    # Determine which curriculum blocks have not been passed yet
    g = solve_curriculum(courseinfo, curriculum, passed_classes)

    # Extract recommended courses from solved plan
    return _extract_active_fillers(g)


def _find_corequirements(out: list[str], expr: Expr):
    if isinstance(expr, ReqCourse) and expr.coreq:
        out.append(expr.code)
    elif isinstance(expr, And | Or):
        for child in expr.children:
            _find_corequirements(out, child)


def _get_corequirements(courseinfo: CourseInfo, courseid: PseudoCourse) -> list[str]:
    out: list[str] = []
    info = None
    if isinstance(courseid, EquivalenceId):
        equiv_info = courseinfo.try_equiv(courseid.code)
        if equiv_info is None or not equiv_info.is_homogeneous:
            return out
        for concrete in equiv_info.courses:
            info = courseinfo.try_course(concrete)
            if info is not None:
                break
    else:
        info = courseinfo.try_course(courseid.code)
    if info is not None:
        _find_corequirements(out, info.deps)
    return out


def _is_course_in_list_of_codes(
    courseinfo: CourseInfo,
    course: PseudoCourse,
    codes: list[str],
) -> bool:
    if isinstance(course, ConcreteId):
        return course.code in codes
    info = courseinfo.try_equiv(course.code)
    if info is None:
        return False
    return any(code in codes for code in info.courses)


def _get_credits(courseinfo: CourseInfo, courseid: PseudoCourse) -> int:
    creds = courseinfo.get_credits(courseid)
    if creds is None:
        creds = 0
    return creds


def _determine_coreq_components(
    courseinfo: CourseInfo,
    courses_to_pass: list[PseudoCourse],
) -> dict[PseudoCourse, list[PseudoCourse]]:
    """
    Determine which courses have to be taken together because they are
    mutual corequirements.
    """

    # First, determine an overall list of corequirements for each course to pass
    coreqs: list[list[str]] = []
    for courseid in courses_to_pass:
        coreqs.append(_get_corequirements(courseinfo, courseid))

    # Start off with each course in its own connected component
    coreq_components: dict[PseudoCourse, list[PseudoCourse]] = {
        courseid: [courseid] for courseid in courses_to_pass
    }

    # Determine which pairs of courses are corequirements of each other
    for i, course1 in enumerate(courses_to_pass):
        for j in range(i + 1, len(courses_to_pass)):
            course2 = courses_to_pass[j]
            if _is_course_in_list_of_codes(
                courseinfo,
                course2,
                coreqs[i],
            ) and _is_course_in_list_of_codes(courseinfo, course1, coreqs[j]):
                # `course1` and `course2` are mutual corequirements, they must be taken
                # together
                # Merge the connected components
                dst = coreq_components[course1]
                src = coreq_components[course2]
                dst.extend(src)
                for c in src:
                    coreq_components[c] = dst

    return coreq_components


def _try_add_course_group(
    courseinfo: CourseInfo,
    plan: ValidatablePlan,
    courses_to_pass: list[PseudoCourse],
    current_credits: int,
    course_group: list[PseudoCourse],
) -> bool:
    """
    Attempt to add a group of courses to the last semester of the given plan.
    Fails if they cannot be added.
    Assumes all courses in the group are not present in the given plan.
    Returns `True` if the courses could be added.
    """

    # Bail if the semestrality is wrong for any course (but it could be right in
    # another semester)
    sem_i = len(plan.classes) - 1
    for course in course_group:
        info = courseinfo.try_course(course.code)
        if info is None:
            continue
        if not info.semestrality[sem_i % 2] and info.semestrality[(sem_i + 1) % 2]:
            return False

    # Determine total credits of this group
    group_credits = sum(_get_credits(courseinfo, c) for c in course_group)

    # Bail if there is not enough space in this semester
    if current_credits + group_credits > RECOMMENDED_CREDITS_PER_SEMESTER:
        return False

    # Temporarily add to plan
    semester = plan.classes[-1]
    original_length = len(semester)
    for course in course_group:
        semester.append(course)

    # Check the dependencies for each course
    for i, course in enumerate(course_group):
        if courseinfo.try_course(course.code) is None:
            continue
        if not quick_validate_dependencies(
            courseinfo,
            plan,
            len(plan.classes) - 1,
            original_length + i,
        ):
            # Requirements are not met
            # Undo changes and cancel
            while len(semester) > original_length:
                semester.pop()
            return False

    # Added course successfully
    # Remove added courses from `courses_to_pass`
    for course in course_group:
        courses_to_pass.remove(course)

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
        classes=classes,
        level=Level.PREGRADO,
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
    courseinfo = await course_info()
    curriculum = await get_curriculum(passed.curriculum)

    # Flat list of all curriculum courses left to pass
    courses_to_pass = _compute_courses_to_pass(courseinfo, curriculum, passed.classes)

    plan = passed.copy(deep=True)
    plan.classes.append([])

    # Precompute corequirements for courses
    coreq_components = _determine_coreq_components(courseinfo, courses_to_pass)

    while courses_to_pass:
        # Attempt to add a single course at the end of the last semester

        # Precompute the amount of credits in this semester
        credits = sum(_get_credits(courseinfo, c) for c in plan.classes[-1])

        # Go in order, attempting to add each course to the semester
        added_course = False
        for try_course in courses_to_pass:
            course_group = coreq_components[try_course]

            could_add = _try_add_course_group(
                courseinfo,
                plan,
                courses_to_pass,
                credits,
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
        if len(plan.classes) >= 2 and not plan.classes[-1] and not plan.classes[-2]:
            # Stuck :(
            break

        # Maybe some requirements are not met, maybe the semestrality is wrong, maybe
        # we reached the credit limit for this semester
        # Anyway, if we are stuck let's try adding a new semester and see if it helps
        plan.classes.append([])

    # Remove empty semesters at the end (if any)
    while plan.classes and not plan.classes[-1]:
        plan.classes.pop()

    if courses_to_pass:
        print(f"WARNING: could not add courses {courses_to_pass}")
        plan.classes.append(courses_to_pass)

    return plan
