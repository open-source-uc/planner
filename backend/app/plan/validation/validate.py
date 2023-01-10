from .curriculum.diagnose import diagnose_curriculum
from .curriculum.tree import CurriculumSpec
from .courses.validate import PlanContext
from ..courseinfo import course_info
from ...sync.siding.translate import fetch_curriculum_from_siding
from .diagnostic import ValidationResult
from ..plan import ValidatablePlan


async def diagnose_plan(
    plan: ValidatablePlan, curriculum_spec: CurriculumSpec
) -> ValidationResult:
    courseinfo = await course_info()
    curriculum = await fetch_curriculum_from_siding(curriculum_spec)
    out = ValidationResult(diagnostics=[])

    # Ensure course requirements are met
    course_ctx = PlanContext(courseinfo, plan)
    course_ctx.validate(out)

    # Ensure the given curriculum is fulfilled
    diagnose_curriculum(courseinfo, curriculum, plan, out)

    return out


async def diagnose_plan_skip_curriculum(plan: ValidatablePlan) -> ValidationResult:
    courseinfo = await course_info()
    out = ValidationResult(diagnostics=[])

    course_ctx = PlanContext(courseinfo, plan)
    course_ctx.validate(out)

    return out
