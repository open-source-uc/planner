from collections import defaultdict

from fastapi import HTTPException

from app.plan.course import PseudoCourse
from app.plan.courseinfo import CourseInfo
from app.plan.plan import ValidatablePlan
from app.plan.validation.curriculum.solve import (
    SolvedCurriculum,
    solve_curriculum,
)
from app.plan.validation.curriculum.tree import Curriculum
from app.plan.validation.diagnostic import (
    CurriculumErr,
    NoMajorMinorWarn,
    UnassignedWarn,
    ValidationResult,
)
from app.user.info import StudentContext


def _diagnose_blocks(
    courseinfo: CourseInfo,
    out: ValidationResult,
    g: SolvedCurriculum,
):
    def fetch_name(filler: PseudoCourse):
        info = courseinfo.try_any(filler)
        return (filler, "?" if info is None else info.name)

    # TODO: If there are several alternatives to fill a gap in the curriculum, show all
    # of them

    # Get any fillers in use
    for usable in g.usable.values():
        for inst in usable.instances:
            if inst.filler is None or inst.flow == 0:
                continue

            options: list[list[PseudoCourse]] = g.find_swapouts(inst)

            # This filler is active, therefore something is missing
            out.add(
                CurriculumErr(
                    blocks=[
                        [
                            block.name
                            for block in layer.active_edge.block_path
                            if block.name is not None
                        ]
                        for layer in inst.layers.values()
                        if layer.active_edge is not None
                    ],
                    credits=inst.flow,
                    fill_options=[
                        fetch_name(filler) for option in options for filler in option
                    ],
                ),
            )


def diagnose_curriculum(
    courseinfo: CourseInfo,
    curriculum: Curriculum,
    plan: ValidatablePlan,
    user_ctx: StudentContext | None,
    out: ValidationResult,
):
    # Produce a warning if no major/minor is selected
    if plan.curriculum.major is None or plan.curriculum.minor is None:
        out.add(NoMajorMinorWarn(plan=plan.curriculum))

    # Solve plan
    g = solve_curriculum(courseinfo, plan.curriculum, curriculum, plan.classes)
    g.forbid_recolor()

    # Generate diagnostics
    _diagnose_blocks(courseinfo, out, g)

    # Count unassigned credits (including passed courses)
    rep_counter: defaultdict[str, int] = defaultdict(lambda: 0)
    unassigned: int = 0
    unassigned_notpassed: bool = False
    first_unvalidated_sem = 0 if user_ctx is None else user_ctx.next_semester
    for sem_i, sem in enumerate(plan.classes):
        for course in sem:
            rep_idx = rep_counter[course.code]
            rep_counter[course.code] += 1
            if course.code in g.superblocks and rep_idx < len(
                g.superblocks[course.code],
            ):
                superblock = g.superblocks[course.code][rep_idx]
                if superblock == "":
                    unassigned += courseinfo.get_credits(course) or 0
                    if sem_i >= first_unvalidated_sem:
                        unassigned_notpassed = True
    if unassigned_notpassed and unassigned > 0:
        out.add(UnassignedWarn(unassigned_credits=unassigned))

    # Tag each course with its associated superblock
    superblocks = {}
    for code, count in rep_counter.items():
        superblocks[code] = ["" for _ in range(count)]
        for rep_idx in range(count):
            if code in g.superblocks and rep_idx < len(g.superblocks[code]):
                superblocks[code][rep_idx] = g.superblocks[code][rep_idx]
    out.course_superblocks = superblocks


def find_swapouts(
    courseinfo: CourseInfo,
    curriculum: Curriculum,
    plan: ValidatablePlan,
    sem_idx: int,
    class_idx: int,
) -> list[list[PseudoCourse]]:
    # Determine the course code and instance index
    if sem_idx >= len(plan.classes) or class_idx >= len(plan.classes[sem_idx]):
        raise HTTPException(400, "invalid class index")
    code = plan.classes[sem_idx][class_idx].code
    instance_idx = 0
    for sem_i, sem in enumerate(plan.classes):
        for cl_i, cl in enumerate(sem):
            if sem_i == sem_idx and cl_i == class_idx:
                break
            if cl.code == code:
                instance_idx += 1
        if sem_i == sem_idx:
            break

    # Solve the plan first
    g = solve_curriculum(courseinfo, plan.curriculum, curriculum, plan.classes)

    # Now, get the equivalents for the given class
    return g.find_swapouts(g.usable[code].instances[instance_idx])
