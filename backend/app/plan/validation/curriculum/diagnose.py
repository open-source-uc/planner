from ...course import PseudoCourse
from .solve import RecommendedCourse, SolvedCurriculum, TakenCourse, solve_curriculum
from ...plan import ClassId, ValidatablePlan
from ..diagnostic import (
    CurriculumErr,
    NoMajorMinorWarn,
    UnassignedWarn,
    ValidationResult,
)
from .tree import Block, Curriculum
from ...courseinfo import CourseInfo


def _diagnose_block(
    courseinfo: CourseInfo,
    diagnosed: dict[str, set[int]],
    out: ValidationResult,
    g: SolvedCurriculum,
    id: int,
    name: str,
) -> list[PseudoCourse]:
    node = g.nodes[id]
    if isinstance(node.origin, tuple):
        _layer, c = node.origin
        if isinstance(c, RecommendedCourse):
            # Make sure to diagnose each course at most once
            diagnosed_insts = diagnosed.setdefault(c.rec.course.code, set())
            if c.repeat_index in diagnosed_insts:
                return []
            diagnosed_insts.add(c.repeat_index)

            # Diagnose this course
            return [c.rec.course]
        else:
            return []
    else:
        my_name = None
        if isinstance(node.origin, Block) and node.origin.name is not None:
            my_name = node.origin.name
        if my_name is not None:
            if name != "":
                name += " -> "
            name += my_name

        needs_diagnosis: list[PseudoCourse] = []
        for edge in node.incoming:
            if edge.flow <= 0:
                continue
            needs_diagnosis.extend(
                _diagnose_block(courseinfo, diagnosed, out, g, edge.src, name)
            )

        if needs_diagnosis and (my_name is not None or id == g.root):
            if name == "":
                name = "?"
            credits = 0
            for c in needs_diagnosis:
                cred = courseinfo.get_credits(c)
                if cred is not None:
                    credits += cred
            out.add(
                CurriculumErr(block=name, credits=credits, recommend=needs_diagnosis)
            )
            return []
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
                list_of_sb.append("")
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
        out.add(NoMajorMinorWarn(plan=plan.curriculum))

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
    unassigned: list[ClassId] = []
    for code, instances in out.course_superblocks.items():
        for rep_idx, superblock in enumerate(instances):
            if superblock == "":
                unassigned.append(ClassId(code=code, instance=rep_idx))
    if unassigned:
        out.add(UnassignedWarn(associated_to=unassigned))
