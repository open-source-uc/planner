from .curriculum.diagnose import diagnose_curriculum
from .curriculum.tree import CurriculumSpec
from .courses.validate import CourseInstance, PlanContext, is_satisfied, sanitize_plan
from ..courseinfo import CourseInfo, course_info
from ...sync.siding.translate import fetch_curriculum_from_siding
from .diagnostic import ValidationResult
from ..plan import PseudoCourse, ValidatablePlan


async def diagnose_plan(
    plan: ValidatablePlan, curriculum_spec: CurriculumSpec
) -> ValidationResult:
    courseinfo = await course_info()
    curriculum = await fetch_curriculum_from_siding(courseinfo, curriculum_spec)
    out = ValidationResult(diagnostics=[])

    # Ensure all courses are known
    plan = sanitize_plan(courseinfo, out, plan)

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


def quick_validate_dependencies(
    courseinfo: CourseInfo,
    plan: ValidatablePlan,
    semester: int,
    course: PseudoCourse,
) -> bool:
    assert courseinfo.try_course(course.code)
    course_ctx = PlanContext(courseinfo, plan)
    return is_satisfied(
        course_ctx,
        CourseInstance(course, semester),
        courseinfo.course(course.code).deps,
    )
