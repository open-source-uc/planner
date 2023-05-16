from typing import Literal, Optional
from .validation.curriculum.solve import SolvedCurriculum, solve_curriculum

from fastapi import HTTPException
from ..user.auth import UserKey
from ..sync import get_curriculum
from .validation.courses.logic import And, Expr, Or, ReqCourse
from .validation.curriculum.tree import (
    LATEST_CYEAR,
    Block,
    Curriculum,
    CurriculumSpec,
    Cyear,
)
from .plan import (
    ClassIndex,
    Level,
    PseudoCourse,
    ValidatablePlan,
)
from .course import EquivalenceId
from .courseinfo import CourseInfo, course_info
from .validation.validate import quick_validate_dependencies
from .. import sync

MAX_CREDITS_PER_SEMESTER = 50


def _extract_recommendations(
    courseinfo: CourseInfo,
    to_pass: list[tuple[int, PseudoCourse]],
    g: SolvedCurriculum,
    id: int,
):
    """
    Recursively visit the curriculum blocks, looking for missing credits.
    If missing credits are found, `to_pass` is filled with the corresponding
    recommended courses in the `fill_with` fields.
    """
    node = g.nodes[id]
    missing = node.cap() - node.flow()
    if missing <= 0:
        return
    if isinstance(node.origin, Block):
        for priority, course in node.origin.fill_with:
            # Get the amount of credits for this pseudocourse
            creds = courseinfo.get_credits(course)
            if creds is None:
                continue
            if creds == 0:
                creds = 1
            # Limit credits if `course` is an equivalence
            if creds > missing and isinstance(course, EquivalenceId):
                course = EquivalenceId(code=course.code, credits=missing)
                creds = missing
            # Add this course to the courses to pass, and reduce the missing credits
            to_pass.append((priority, course))
            missing -= creds
            if missing <= 0:
                break
        if len(node.origin.fill_with) > 0:
            # Stop the search at the first nonempty `fill_with`
            # Remember that every path from root to leaf should have at most 1 node
            # with courses in `fill_with`
            return
    # Recursively extract recommendations from child nodes
    for edge in node.incoming:
        if edge.cap == 0:
            continue
        _extract_recommendations(courseinfo, to_pass, g, edge.src)


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

    # A list of courses associated to a priority
    # The priority indicates if the course should be taken early or late in the
    # student's career plan
    to_pass: list[tuple[int, PseudoCourse]] = []
    _extract_recommendations(courseinfo, to_pass, g, g.root)

    # Order recommendations by priority, from soonest to latest
    to_pass.sort(key=lambda priority_course: priority_course[0])

    # Remove priority information, since it is redundant with the order of the list
    return list(map(lambda priority_course: priority_course[1], to_pass))


def _find_corequirements(out: list[str], expr: Expr):
    if isinstance(expr, ReqCourse) and expr.coreq:
        out.append(expr.code)
    elif isinstance(expr, (And, Or)):
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
    courseinfo: CourseInfo, course: PseudoCourse, codes: list[str]
) -> bool:
    if isinstance(course, EquivalenceId):
        info = courseinfo.try_equiv(course.code)
        if info is None:
            return False
        for code in info.courses:
            if code in codes:
                return True
        return False
    else:
        return course.code in codes


def _get_credits(courseinfo: CourseInfo, courseid: PseudoCourse) -> int:
    creds = courseinfo.get_credits(courseid)
    if creds is None:
        creds = 0
    return creds


def _determine_coreq_components(
    courseinfo: CourseInfo, courses_to_pass: list[PseudoCourse]
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
                courseinfo, course2, coreqs[i]
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
) -> Literal["credits", "deps", "added"]:
    """
    Attempt to add a group of courses to the last semester of the given plan.
    Fails if they cannot be added.
    Assumes all courses in the group are not present in the given plan.
    """

    # Determine total credits of this group
    group_credits = sum(map(lambda c: _get_credits(courseinfo, c), course_group))

    # Bail if there is not enough space in this semester
    if current_credits + group_credits > MAX_CREDITS_PER_SEMESTER:
        return "credits"

    # Temporarily add to plan
    semester = plan.classes[-1]
    original_length = len(semester)
    for course in course_group:
        semester.append(course)

    # Check the dependencies for each course
    for i, course in enumerate(course_group):
        if courseinfo.try_course(course.code) is None:
            continue
        index = ClassIndex(semester=len(plan.classes) - 1, position=original_length + i)
        if not quick_validate_dependencies(courseinfo, plan, index, course):
            # Requirements are not met
            # Undo changes and cancel
            while len(semester) > original_length:
                semester.pop()
            return "deps"

    # Added course successfully
    # Remove added courses from `courses_to_pass`
    for course in course_group:
        courses_to_pass.remove(course)

    return "added"


async def generate_empty_plan(user: Optional[UserKey] = None) -> ValidatablePlan:
    """
    Generate an empty plan with optional user context.
    If no user context is available, uses the latest curriculum version.

    All plans are born from this function (or deserialized from plans that were born
    from this function, except for manually crafted plans).
    """
    # TODO: Support empty major/minor/title selection
    classes: list[list[PseudoCourse]]
    next_semester: int
    curriculum: CurriculumSpec
    if user is None:
        classes = []
        next_semester = 0
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
            # HTTP error 501: Unimplemented
            # TODO: The frontend could recognize this code and show a nice error message
            # maybe?
            raise HTTPException(
                status_code=501, detail="Your curriculum version is unsupported"
            )
        classes = student.passed_courses
        next_semester = len(classes)
        curriculum = CurriculumSpec(
            cyear=cyear,
            major=student.info.reported_major,
            minor=student.info.reported_minor,
            title=student.info.reported_title,
        )
    return ValidatablePlan(
        classes=classes,
        next_semester=next_semester,
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

    print(f"courses_to_pass: {courses_to_pass}")

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
        could_use_more_credits = False
        some_requirements_missing = False
        for try_course in courses_to_pass:
            course_group = coreq_components[try_course]

            status = _try_add_course_group(
                courseinfo, plan, courses_to_pass, credits, course_group
            )
            if status == "added":
                # Successfully added a course, finish
                added_course = True
                break
            elif status == "credits":
                # Keep track of the case when there are some courses that need more
                # credit-space
                could_use_more_credits = True
            elif status == "deps":
                # Keep track on when we need more requirements
                some_requirements_missing = True

        if added_course:
            # Made some progress!
            # Continue adding courses
            continue

        if could_use_more_credits:
            # Maybe we couldn't make progress because there is no space for any more
            # courses
            plan.classes.append([])
            continue

        if some_requirements_missing and len(plan.classes[-1]) != 0:
            # Last chance: maybe we can't make progress because there's a course that
            # depends on the courses on this very semester
            plan.classes.append([])
            continue

        # Stuck! :(
        break

    if courses_to_pass:
        print(f"WARNING: could not add courses {courses_to_pass}")
        plan.classes.append(courses_to_pass)

    return plan
