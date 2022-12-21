from .curriculum.validate import diagnose_curriculum
from .curriculum.tree import Curriculum
from .courses.validate import PlanContext
from .courseinfo import course_info
from .plan import ValidatablePlan, ValidationResult


async def diagnose_plan(
    plan: ValidatablePlan, curriculum: Curriculum
) -> ValidationResult:
    courseinfo = await course_info()
    out = ValidationResult(diagnostics=[])

    # Ensure course requirements are met
    course_ctx = PlanContext(courseinfo, plan)
    course_ctx.validate(out)

    # Ensure the given curriculum is fulfilled
    diagnose_curriculum(courseinfo, curriculum, plan, out)

    return out
