from .solve import RecommendedCourse, SolvedCurriculum, TakenCourse, solve_curriculum
from ...plan import ValidatablePlan
from ..diagnostic import DiagnosticErr, DiagnosticWarn, ValidationResult
from .tree import Block, Curriculum
from ...courseinfo import CourseInfo


class CurriculumErr(DiagnosticErr):
    missing: str
    credits: int

    def message(self) -> str:
        return f"""Faltan {self.credits} créditos para el bloque {self.missing}"""


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


def _diagnose_block(
    courseinfo: CourseInfo,
    diagnosed: dict[str, set[int]],
    out: ValidationResult,
    g: SolvedCurriculum,
    id: int,
    name: str,
) -> int:
    node = g.nodes[id]
    if isinstance(node.origin, tuple):
        _layer, c = node.origin
        if isinstance(c, RecommendedCourse):
            # Make sure to diagnose each course at most once
            diagnosed_insts = diagnosed.setdefault(c.rec.course.code, set())
            if c.repeat_index in diagnosed_insts:
                return 0
            diagnosed_insts.add(c.repeat_index)

            # Mark that this amount of credits have to be diagnosed
            creds = courseinfo.get_credits(c.rec.course)
            if creds is None:
                return 0
            elif creds == 0:
                return 1
            else:
                return creds
        else:
            return 0
    else:
        my_name = None
        if isinstance(node.origin, Block) and node.origin.name is not None:
            my_name = node.origin.name
        if my_name is not None:
            if name != "":
                name += " -> "
            name += my_name

        needs_diagnosis = 0
        for edge in node.incoming:
            if edge.flow <= 0:
                continue
            needs_diagnosis += _diagnose_block(
                courseinfo, diagnosed, out, g, edge.src, name
            )

        if needs_diagnosis > 0 and (my_name is not None or id == g.root):
            if name == "":
                name = "?"
            out.add(CurriculumErr(missing=name, credits=needs_diagnosis))
            return 0
        else:
            return needs_diagnosis


def _tag_superblock(
    superblock: str, out: ValidationResult, g: SolvedCurriculum, id: int
):
    node = g.nodes[id]
    if isinstance(node.origin, tuple):
        layer, c = node.origin
        if layer == "" and isinstance(c, TakenCourse):
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
    _diagnose_block(courseinfo, {}, out, g, g.root, "")

    # Tag each course with its associated superblock
    for edge in g.nodes[g.root].incoming:
        if edge.cap == 0:
            continue
        node = g.nodes[edge.src]
        if isinstance(node.origin, Block) and node.origin.name is not None:
            _tag_superblock(node.origin.name, out, g, edge.src)

    # Send warning for each unassigned course (including passed courses)
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
