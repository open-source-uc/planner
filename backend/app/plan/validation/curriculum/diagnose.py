from .solve import SolvedBlock, SolvedNode, solve_curriculum
from ...plan import PseudoCourse, ValidatablePlan
from ..diagnostic import DiagnosticErr, DiagnosticWarn, ValidationResult
from .tree import Curriculum
from ...courseinfo import CourseInfo


class CurriculumErr(DiagnosticErr):
    superblock: str
    missing: str

    def message(self) -> str:
        return f"""Se deben completar los créditos de '{self.superblock}'.
        Falta lo siguiente: {self.missing}"""


class UnassignedWarn(DiagnosticWarn):
    code: str

    def course_code(self) -> str:
        return self.code

    def message(self) -> str:
        return f"El curso {self.code} no cuenta para tu avance curricular"


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


def _is_course_not_passed(plan: ValidatablePlan, code: str) -> bool:
    for sem_i in range(plan.next_semester, len(plan.classes)):
        for c in plan.classes[sem_i]:
            if code == c.code:
                return True
    return False


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

    # Send warning for each unassigned course
    # (Only for courses that have not been passed)
    for code in solved.unassigned_codes:
        if _is_course_not_passed(plan, code):
            out.add(UnassignedWarn(code=code))
