from app.plan.courseinfo import course_info
from app.plan.plan import ValidatablePlan
from app.plan.validation.courses.validate import ValidationContext
from app.plan.validation.curriculum.diagnose import diagnose_curriculum
from app.plan.validation.diagnostic import ValidationResult
from app.plan.validation.user import validate_against_owner
from app.sync import get_curriculum
from app.user.info import StudentContext


async def diagnose_plan(
    plan: ValidatablePlan,
    user_ctx: StudentContext | None,
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
    course_ctx = ValidationContext(courseinfo, plan, user_ctx)
    course_ctx.validate_all(out)

    # Ensure the given curriculum is fulfilled
    diagnose_curriculum(courseinfo, curriculum, plan, user_ctx, out)

    # Validate against user context, if there is any context
    if user_ctx is not None:
        validate_against_owner(plan, user_ctx, out)

    return out
