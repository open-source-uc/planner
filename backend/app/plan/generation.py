from .validation.courses.logic import And, Expr, Or, ReqCourse
from .validation.curriculum.tree import CurriculumSpec
from .plan import ValidatablePlan
from .courseinfo import CourseInfo, course_info
from .validation.validate import quick_validate_dependencies
from ..sync.siding.translate import fetch_recommended_courses_from_siding


class CurriculumRecommender:
    """
    Encapsulates all the recommendation logic.
    Scalable and extensible for future curriculum recommendation strategies.
    """

    CREDITS_PER_SEMESTER = 50

    @classmethod
    async def recommend(cls, curr: CurriculumSpec) -> ValidatablePlan:
        courses = await fetch_recommended_courses_from_siding(curr)
        return ValidatablePlan(classes=courses, next_semester=0)


def _compute_courses_to_pass(
    curriculum_classes: list[list[str]], passed_classes: list[list[str]]
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


def _clone_plan(plan: ValidatablePlan):
    classes: list[list[str]] = []
    for semester in plan.classes:
        classes.append(semester.copy())
    return ValidatablePlan(
        classes=classes,
        next_semester=plan.next_semester,
        level=plan.level,
        school=plan.school,
        career=plan.career,
    )


def _find_corequirements(out: list[str], expr: Expr):
    if isinstance(expr, ReqCourse) and expr.coreq:
        out.append(expr.code)
    elif isinstance(expr, (And, Or)):
        for child in expr.children:
            _find_corequirements(out, child)


def _determine_coreq_components(
    courseinfo: dict[str, CourseInfo], courses_to_pass: list[str]
) -> dict[str, list[str]]:
    """
    Determine which courses have to be taken together because they are
    mutual corequirements.
    """
    coreq_components: dict[str, list[str]] = {}
    for course in courses_to_pass:
        # Find corequirements of this course
        coreqs: list[str] = []
        if course in courseinfo:
            _find_corequirements(coreqs, courseinfo[course].deps)
        # Filter corequirements only to mutual corequirements
        mutual_coreqs = [course]
        for coreq in coreqs:
            coreqs_of_coreq: list[str] = []
            if coreq in courseinfo and coreq in courses_to_pass:
                _find_corequirements(coreqs_of_coreq, courseinfo[coreq].deps)
            if course in coreqs_of_coreq:
                mutual_coreqs.append(coreq)
        # Associate this course to its mutual courses
        coreq_components[course] = mutual_coreqs
    return coreq_components


def _try_add_course_group(
    courseinfo: dict[str, CourseInfo],
    plan: ValidatablePlan,
    courses_to_pass: list[str],
    current_credits: int,
    course_group: list[str],
):
    """
    Attempt to add a group of courses to the last semester of the given plan.
    Fails if they cannot be added.
    Assumes all courses in the group are not present in the given plan.
    """

    # Determine total credits of this group
    group_credits = sum(
        map(lambda c: courseinfo[c].credits if c in courseinfo else 10, course_group)
    )

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
        if course not in courseinfo:
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


async def generate_default_plan(passed: ValidatablePlan, curriculum: CurriculumSpec):
    recommended = await CurriculumRecommender.recommend(curriculum)
    courseinfo = await course_info()

    # flat list of all curriculum courses left to pass
    courses_to_pass = _compute_courses_to_pass(recommended.classes, passed.classes)

    for course in courses_to_pass:
        if course not in courseinfo:
            print(
                f"WARNING: course {course} not found in database. "
                "assuming 10 credits and no requirements."
            )

    plan = _clone_plan(passed)
    plan.classes.append([])

    # Precompute corequirements for courses
    coreq_components = _determine_coreq_components(courseinfo, courses_to_pass)

    while courses_to_pass:
        # Attempt to add a single course at the end of the last semester

        # Precompute the amount of credits in this semester
        credits = sum(
            courseinfo[c].credits if c in courseinfo else 10 for c in plan.classes[-1]
        )

        # Go in order, attempting to add each course to the semester
        added_course = False
        could_use_more_credits = False
        for try_course in courses_to_pass:
            course_group = list(
                filter(lambda c: c in courses_to_pass, coreq_components[try_course])
            )

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
