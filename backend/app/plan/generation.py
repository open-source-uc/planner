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


def _try_add_course(
    courseinfo: dict[str, CourseInfo],
    plan: ValidatablePlan,
    go_together: dict[str, list[str]],
    courses_to_pass: list[str],
    credits: int,
    try_course: str,
):
    # Treat unknown courses specially
    if try_course not in courseinfo:
        if credits + 10 <= CurriculumRecommender.CREDITS_PER_SEMESTER:
            print(
                f"WARNING: unknown course {try_course} found while generating "
                "plan. assuming 10 credits and adding as-is."
            )
            plan.classes[-1].append(try_course)
            courses_to_pass.remove(try_course)
            return "added"
        else:
            print(
                f"WARNING: unknown course {try_course} found while generating "
                "plan. skipping because there is no space for 10 credits."
            )
            return "credits"

    # Do not add if we would take too many credits
    if (
        credits + courseinfo[try_course].credits
        > CurriculumRecommender.CREDITS_PER_SEMESTER
    ):
        return "credits"

    # Do not add if it would break some requirement
    original_length = len(plan.classes[-1])
    for subcourse in go_together[try_course]:
        if subcourse in courses_to_pass:
            plan.classes[-1].append(subcourse)
    for i in range(original_length, len(plan.classes[-1])):
        if not quick_validate_dependencies(
            courseinfo, plan, len(plan.classes) - 1, plan.classes[-1][i]
        ):
            # Found a requirement error
            # Undo changes and cancel
            while len(plan.classes[-1]) > original_length:
                plan.classes[-1].pop()
            return "cant"

    # Added course successfully
    # Remove added courses from `courses_to_pass`
    for i in range(original_length, len(plan.classes[-1])):
        courses_to_pass.remove(plan.classes[-1][i])

    return "added"


async def generate_default_plan(passed: ValidatablePlan, curriculum: CurriculumSpec):
    recommended = await CurriculumRecommender.recommend(curriculum)
    courseinfo = await course_info()

    # flat list of all curriculum courses left to pass
    courses_to_pass = _compute_courses_to_pass(recommended.classes, passed.classes)

    plan = _clone_plan(passed)
    plan.classes.append([])

    # Precompute corequirements for courses
    go_together: dict[str, list[str]] = {}
    for course in courses_to_pass:
        coreqs = [course]
        if course in courseinfo:
            _find_corequirements(coreqs, courseinfo[course].deps)
        coreqs = list(filter(lambda c: c in courses_to_pass, coreqs))
        go_together[course] = coreqs

    while courses_to_pass:
        # Attempt to add a single course at the end of the last semester

        # Precompute the amount of credits in this semester
        credits = sum(
            courseinfo[c].credits if c in courseinfo else 0 for c in plan.classes[-1]
        )

        # Go in order, attempting to add each course to the semester
        added_course = False
        could_use_more_credits = False
        for try_course in courses_to_pass:
            status = _try_add_course(
                courseinfo, plan, go_together, courses_to_pass, credits, try_course
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
        print(f"WARNING: could not add courses {courses_to_pass}")
        break

    return plan
