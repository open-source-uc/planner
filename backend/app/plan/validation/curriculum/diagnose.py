from .solve import SolvedCurriculum, solve_curriculum
from ...plan import ClassIndex, ValidatablePlan
from ..diagnostic import DiagnosticErr, DiagnosticWarn, ValidationResult
from .tree import Block, Curriculum
from ...courseinfo import CourseInfo


class CurriculumErr(DiagnosticErr):
    missing: str

    def message(self) -> str:
        return f"""Faltan créditos para el bloque {self.missing}"""


class UnassignedWarn(DiagnosticWarn):
    index: ClassIndex
    code: str

    def course_index(self) -> ClassIndex:
        return self.index

    def message(self) -> str:
        return f"El curso {self.code} no cuenta para tu avance curricular"


class MustSelectCurriculumErr(DiagnosticErr):
    has_major: bool
    has_minor: bool

    def message(self):
        missing: list[str] = []
        if not self.has_major:
            missing.append("major")
        if not self.has_minor:
            missing.append("minor")
        return f"Falta seleccionar {' y '.join(missing)}"


def _diagnose_block(out: ValidationResult, g: SolvedCurriculum, id: int, name: str):
    node = g.nodes[id]
    if node.flow() >= node.cap():
        return False
    my_name = None
    if isinstance(node.origin, Block) and node.origin.name is not None:
        my_name = node.origin.name
    if my_name is not None:
        if name != "":
            name += " -> "
        name += my_name
    diagnosed = False
    for edge in node.incoming:
        if edge.cap == 0:
            continue
        subdiagnosed = _diagnose_block(out, g, edge.src, name)
        diagnosed = diagnosed or subdiagnosed
    if not diagnosed and (my_name is not None or id == g.root):
        if name == "":
            name = "?"
        out.add(CurriculumErr(missing=name))
    return True


def _tag_superblock(
    superblock: str, out: ValidationResult, g: SolvedCurriculum, id: int
):
    node = g.nodes[id]
    if isinstance(node.origin, tuple):
        layer, index = node.origin
        if layer == "":
            out.course_superblocks[index.semester][index.position] = superblock
    else:
        for edge in node.incoming:
            if edge.flow <= 0:
                continue
            _tag_superblock(superblock, out, g, edge.src)


def diagnose_curriculum(
    courseinfo: CourseInfo,
    curriculum: Curriculum,
    plan: ValidatablePlan,
    out: ValidationResult,
):
    # Produce a warning if no major/minor is selected
    if plan.curriculum.major is None or plan.curriculum.minor is None:
        out.add(
            MustSelectCurriculumErr(
                has_major=plan.curriculum.major is not None,
                has_minor=plan.curriculum.minor is not None,
            )
        )

    # Solve plan
    g = solve_curriculum(courseinfo, curriculum, plan.classes)

    # Generate diagnostics
    _diagnose_block(out, g, g.root, "")

    # Tag each course with its associated superblock
    for edge in g.nodes[g.root].incoming:
        if edge.cap == 0:
            continue
        node = g.nodes[edge.src]
        if isinstance(node.origin, Block) and node.origin.name is not None:
            _tag_superblock(node.origin.name, out, g, edge.src)

    # Send warning for each unassigned course
    # (Only for courses that have not been passed)
    for sem_i in range(plan.next_semester, len(plan.classes)):
        sem = plan.classes[sem_i]
        for i, c in enumerate(sem):
            index = ClassIndex(semester=sem_i, position=i)
            if out.course_superblocks[index.semester][index.position] is None:
                out.add(UnassignedWarn(index=index, code=c.code))
