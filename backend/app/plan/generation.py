from typing import Optional

from fastapi import HTTPException
from ..user.auth import UserKey
from ..sync import get_recommended_plan
from .validation.courses.logic import And, Expr, Or, ReqCourse
from .validation.curriculum.tree import CurriculumSpec, Cyear
from .plan import EquivalenceId, Level, PseudoCourse, ValidatablePlan
from .courseinfo import CourseInfo, course_info
from .validation.validate import quick_validate_dependencies
from .. import sync


class CurriculumRecommender:
    """
    Encapsulates all the recommendation logic.
    Scalable and extensible for future curriculum recommendation strategies.
    """

    CREDITS_PER_SEMESTER = 50

    @classmethod
    async def recommend(
        cls, courseinfo: CourseInfo, curr: CurriculumSpec
    ) -> list[list[PseudoCourse]]:
        return await get_recommended_plan(curr)


def _compute_courses_to_pass(
    curriculum_classes: list[list[PseudoCourse]],
    passed_classes: list[list[PseudoCourse]],
):
    flat_curriculum_classes = [
        item for sublist in curriculum_classes for item in sublist
    ]
    return list(
        filter(
            lambda course: all(course not in passed for passed in passed_classes),
            flat_curriculum_classes,
        )
    )


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
    if isinstance(courseid, EquivalenceId):
        return courseid.credits
    else:
        info = courseinfo.try_course(courseid.code)
        if info is None:
            return 0
        return info.credits


def _determine_coreq_components(
    courseinfo: CourseInfo, courses_to_pass: list[PseudoCourse]
) -> dict[str, list[PseudoCourse]]:
    """
    Determine which courses have to be taken together because they are
    mutual corequirements.
    """

    # First, determine an overall list of corequirements for each course to pass
    coreqs: list[list[str]] = []
    for courseid in courses_to_pass:
        coreqs.append(_get_corequirements(courseinfo, courseid))

    # Start off with each course in its own connected component
    coreq_components: dict[str, list[PseudoCourse]] = {
        courseid.code: [courseid] for courseid in courses_to_pass
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
                dst = coreq_components[course1.code]
                src = coreq_components[course2.code]
                dst.extend(src)
                for c in src:
                    coreq_components[c.code] = dst

    return coreq_components


def _try_add_course_group(
    courseinfo: CourseInfo,
    plan: ValidatablePlan,
    courses_to_pass: list[PseudoCourse],
    current_credits: int,
    course_group: list[PseudoCourse],
):
    """
    Attempt to add a group of courses to the last semester of the given plan.
    Fails if they cannot be added.
    Assumes all courses in the group are not present in the given plan.
    """

    # Determine total credits of this group
    group_credits = sum(map(lambda c: _get_credits(courseinfo, c), course_group))

    # Bail if there is not enough space in this semester
    if current_credits + group_credits > CurriculumRecommender.CREDITS_PER_SEMESTER:
        return "credits"

    # Temporarily add to plan
    semester = plan.classes[-1]
    original_length = len(semester)
    for course in course_group:
        semester.append(course)

    # Check the dependencies for each course
    for course in course_group:
        if courseinfo.try_course(course.code) is None:
            continue
        if not quick_validate_dependencies(
            courseinfo, plan, len(plan.classes) - 1, course
        ):
            # Requirements are not met
            # Undo changes and cancel
            while len(semester) > original_length:
                semester.pop()
            return "cant"

    # Added course successfully
    # Remove added courses from `courses_to_pass`
    for course in course_group:
        courses_to_pass.remove(course)

    return "added"


async def generate_empty_plan(user: Optional[UserKey] = None) -> ValidatablePlan:
    """
    MUST BE CALLED WITH AUTHORIZATION

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
            cyear=Cyear.LATEST,
            major="M170",
            minor="N776",
            title="40082",
        )
    else:
        info = await sync.fetch_student_info(user)
        previous = await sync.fetch_student_previous_courses(user, info)
        cyear = Cyear.from_str(info.cyear)
        if cyear is None:
            # HTTP error 501: Unimplemented
            # The frontend could recognize this code and show a nice error message
            # maybe?
            raise HTTPException(
                status_code=501, detail="Your curriculum version is unsupported"
            )
        classes = previous
        next_semester = len(previous)
        curriculum = CurriculumSpec(
            cyear=cyear,
            major=info.reported_major,
            minor=info.reported_minor,
            title=info.reported_title,
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
    recommended = await CurriculumRecommender.recommend(courseinfo, passed.curriculum)

    # Flat list of all curriculum courses left to pass
    courses_to_pass = _compute_courses_to_pass(recommended, passed.classes)

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
        for try_course in courses_to_pass:
            course_group = coreq_components[try_course.code]

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

        if added_course:
            # Made some progress!
            # Continue adding courses
            continue

        if could_use_more_credits:
            # Maybe we couldn't make progress because there is no space for any more
            # courses
            plan.classes.append([])
            continue

        # Stuck! :(
        break

    if courses_to_pass:
        print(f"WARNING: could not add courses {courses_to_pass}")
        plan.classes.append(courses_to_pass)

    return plan
