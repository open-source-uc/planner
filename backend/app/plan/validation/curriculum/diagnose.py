from .solve import SolvedBlock, SolvedNode, solve_curriculum
from ...plan import ValidatablePlan
from ..diagnostic import ValidationResult
from .tree import Curriculum
from ...courseinfo import CourseInfo


def _diagnose_block(out: ValidationResult, block: SolvedBlock, node: SolvedNode):
    if node.flow >= node.cap:
        return
    if isinstance(node, SolvedBlock) and node.is_and:
        report_children = True
        for child in node.children:
            if child.flow < child.cap and child.name is None:
                report_children = False
                break
        if report_children:
            for child in node.children:
                _diagnose_block(out, block, child)
            return
    out.err(f"Faltan ramos para el bloque '{block.name}': Falta {node.name}")


def diagnose_curriculum(
    courseinfo: dict[str, CourseInfo],
    curriculum: Curriculum,
    plan: ValidatablePlan,
    out: ValidationResult,
):
    # Build a set of courses from the plan
    taken_courses: list[str] = []
    for sem in plan.classes:
        for code in sem:
            taken_courses.append(code)

    # Solve plan
    solved = solve_curriculum(courseinfo, curriculum, taken_courses)
    print(f"solved plan: {solved}")

    # Generate diagnostics
    for block in solved.blocks:
        _diagnose_block(out, block, block)
