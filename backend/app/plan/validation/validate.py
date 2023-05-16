from typing import Optional

from .user import validate_against_owner

from ...user.info import StudentContext
from .curriculum.diagnose import diagnose_curriculum
from .courses.validate import CourseInstance, PlanContext, is_satisfied
from ..courseinfo import CourseInfo, course_info
from ...sync import get_curriculum
from .diagnostic import ValidationResult
from ..plan import ClassIndex, PseudoCourse, ValidatablePlan


async def diagnose_plan(
    plan: ValidatablePlan, user_ctx: Optional[StudentContext]
) -> ValidationResult:
    """
    Validate a career plan, checking that all pending courses can actually be taken
    (ie. validate their dependencies), and also check that if the plan is followed the
    user will get their set major/minor/title degree.
    """
    courseinfo = await course_info()
    curriculum = await get_curriculum(plan.curriculum)
    out = ValidationResult.empty(plan)

    # Ensure course requirements are met
    course_ctx = PlanContext(courseinfo, plan)
    course_ctx.validate(out)

    # Ensure the given curriculum is fulfilled
    diagnose_curriculum(courseinfo, curriculum, plan, out)

    # Validate against user context, if there is any context
    if user_ctx is not None:
        validate_against_owner(plan, user_ctx, out)

    return out


async def diagnose_plan_skip_curriculum(plan: ValidatablePlan) -> ValidationResult:
    """
    Validate a career plan, but only the course dependencies.
    Do not validate whether the student will get their selected degree.
    """
    courseinfo = await course_info()
    out = ValidationResult.empty(plan)

    course_ctx = PlanContext(courseinfo, plan)
    course_ctx.validate(out)

    return out


def quick_validate_dependencies(
    courseinfo: CourseInfo,
    plan: ValidatablePlan,
    index: ClassIndex,
    course: PseudoCourse,
) -> bool:
    """
    Simulate placing the given course at the given semester, and check if its
    dependencies are met.
    """
    assert courseinfo.try_course(course.code)
    course_ctx = PlanContext(courseinfo, plan)
    info = courseinfo.try_course(course.code)
    if info is None:
        return False
    return is_satisfied(
        course_ctx,
        CourseInstance(course, index),
        info.deps,
    )
