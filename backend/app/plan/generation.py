from typing import Optional
from .validation.diagnostic import ValidationResult
from .validation.courses.logic import Expr, Operator, ReqCourse
from .validation.courses.validate import RequirementErr
from .validation.curriculum.tree import CurriculumSpec
from .plan import ValidatablePlan
from .courseinfo import course_info
from .validation.validate import diagnose_plan
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
    elif isinstance(expr, Operator):
        for child in expr.children:
            _find_corequirements(out, child)


def _find_requirement_error(
    courses: list[str], result: ValidationResult
) -> Optional[RequirementErr]:
    for diag in result.diagnostics:
        if isinstance(diag, RequirementErr) and diag.code in courses:
            return diag
    return None


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
        credits = sum(
            courseinfo[c].credits if c in courseinfo else 0 for c in plan.classes[-1]
        )

        added_course = False
        could_use_more_credits = False
        for try_course in courses_to_pass:
            # Do not add if we would take too many credits
            if try_course not in courseinfo:
                print(
                    f"WARNING: unknown course {try_course} found while generating plan."
                    " assuming 10 credits"
                )
                creds = 10
            else:
                creds = courseinfo[try_course].credits
            if credits + creds > CurriculumRecommender.CREDITS_PER_SEMESTER:
                could_use_more_credits = True
                continue

            # Do not add if it would break some requirement
            original_length = len(plan.classes[-1])
            to_add: list[str] = []
            for subcourse in go_together[try_course]:
                if subcourse in courses_to_pass:
                    to_add.append(subcourse)
            for subcourse in to_add:
                plan.classes[-1].append(subcourse)
            err = _find_requirement_error(to_add, await diagnose_plan(plan, curriculum))
            if err is not None:
                # Found a requirement error
                print(f"cant add course {try_course}: {err.missing}")
                while len(plan.classes[-1]) > original_length:
                    plan.classes[-1].pop()
                continue

            # Added course successfully
            # Remove added courses from `courses_to_pass`
            for i in range(original_length, len(plan.classes[-1])):
                courses_to_pass.remove(plan.classes[-1][i])

            added_course = True
            break

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
