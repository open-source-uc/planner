from .solve import SolvedCurriculum, solve_curriculum
from ...plan import ValidatablePlan
from ..diagnostic import DiagnosticErr, DiagnosticWarn, ValidationResult
from .tree import Block, Curriculum
from ...courseinfo import CourseInfo


class CurriculumErr(DiagnosticErr):
    missing: str

    def message(self) -> str:
        return f"""Faltan créditos para el bloque {self.missing}"""


class UnassignedWarn(DiagnosticWarn):
    index: tuple[int, int]
    code: str

    def class_index(self) -> tuple[int, int]:
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
        layer, c = node.origin
        if layer == "":
            list_of_sb = out.course_superblocks.setdefault(c.course.code, [])
            while c.repeat_index >= len(list_of_sb):
                list_of_sb.append(None)
            list_of_sb[c.repeat_index] = superblock
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
    counters: dict[str, int] = {}
    for sem_i, sem in enumerate(plan.classes):
        for i, c in enumerate(sem):
            count = counters.get(c.code, 0)
            counters[c.code] = count + 1
            if sem_i >= plan.next_semester and (
                c.code not in out.course_superblocks
                or count >= len(out.course_superblocks[c.code])
                or out.course_superblocks[c.code][count] is None
            ):
                out.add(UnassignedWarn(index=(sem_i, i), code=c.code))
