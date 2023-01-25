from .solve import SolvedBlock, SolvedNode, solve_curriculum
from ...plan import PseudoCourse, ValidatablePlan
from ..diagnostic import DiagnosticErr, ValidationResult
from .tree import Curriculum
from ...courseinfo import CourseInfo


class CurriculumErr(DiagnosticErr):
    superblock: str
    missing: str

    def message(self) -> str:
        return f"""
        Se deben completar los créditos de '{self.superblock}'.
        Falta lo siguiente: {self.missing}
        """


def _diagnose_block(out: ValidationResult, node: SolvedNode):
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
                _diagnose_block(out, child)
            return
    out.add(CurriculumErr(superblock=node.superblock, missing=node.name or "?"))


def diagnose_curriculum(
    courseinfo: CourseInfo,
    curriculum: Curriculum,
    plan: ValidatablePlan,
    out: ValidationResult,
):
    # Build a set of courses from the plan
    taken_courses: list[PseudoCourse] = []
    for sem in plan.classes:
        for courseid in sem:
            taken_courses.append(courseid)

    # Solve plan
    solved = solve_curriculum(courseinfo, curriculum, taken_courses)

    # Generate diagnostics
    for block in solved.blocks:
        _diagnose_block(out, block)

    # Tag each course with its associated superblock
    for code, block in solved.course_assignments.items():
        out.course_superblocks[code] = block.superblock
