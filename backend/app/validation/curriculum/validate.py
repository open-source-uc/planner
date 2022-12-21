from .solve import solve_curriculum
from ..plan import ValidatablePlan, ValidationResult
from .tree import Curriculum
from ..courseinfo import CourseInfo


def diagnose_curriculum(
    courseinfo: dict[str, CourseInfo],
    curriculum: Curriculum,
    plan: ValidatablePlan,
    out: ValidationResult,
):
    # Build a set of courses from the plan
    taken_courses: set[str] = set()
    for sem in plan.classes:
        for code in sem:
            taken_courses.add(code)

    # Solve plan
    solved = solve_curriculum(courseinfo, curriculum, taken_courses)
    print(f"solved plan: {solved}")

    # Generate diagnostics
    for block in solved.blocks:
        if block.flow < block.cap:
            out.err(f"Faltan ramos para el bloque '{block.name}'")
