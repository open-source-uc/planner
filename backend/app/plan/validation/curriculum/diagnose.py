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
    RecolorDiag,
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

    # Remember which courses were recolored
    # Note that courses are only recolored if doing so allows a better plan, so this
    # list contains no unnecessary recolors
    recolors = g.find_recolors()

    # Get any fillers in use
    # Note that at this point recoloring *is* allowed
    # This means that:
    # - If there is a way to recolor the courses such that the curriculum is satisfied,
    #   Planner will always recommend to recolor and will not complain about missing
    #   courses.
    # - If courses *are* missing anyway, Planner will assume that all courses can be
    #   recolored arbitrarily.
    satisfied_with_recoloring = True
    for usable in g.usable.values():
        for inst in usable.instances:
            if not inst.filler or not inst.flow:
                continue

            options: list[list[PseudoCourse]] = g.find_swapouts(inst)

            # This filler is active, therefore something is missing
            satisfied_with_recoloring = False
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

    # Now, forbid recoloring and retry
    if g.forbid_recolor():
        # Reassigning equivalences can save us some courses

        # Check is the curriculum went unsatisfied from the recolor ban
        satisfied_without_recoloring = True
        for usable in g.usable.values():
            for inst in usable.instances:
                if inst.filler and inst.flow:
                    satisfied_without_recoloring = False

        # If the curriculum was satisfied when recoloring, but is now unsatisfied now
        # that no recoloring is allowed, block assignments (ie. colors) are a hard error
        hard_error = satisfied_with_recoloring and not satisfied_without_recoloring

        # Reassigning the equivalences can save us some courses or even fix the
        # curriculum requirements
        out.add(
            RecolorDiag(
                is_err=hard_error,
                associated_to=[id for id, _equiv in recolors],
                recolor_as=[equiv for _id, equiv in recolors],
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
    superblocks: dict[str, list[str]] = {}
    for sem in plan.classes:
        for course in sem:
            code = course.code
            if code not in superblocks:
                superblocks[code] = []
            superblock = ""
            rep_idx = len(superblocks[code])
            if code in g.superblocks and rep_idx < len(g.superblocks[code]):
                superblock = g.superblocks[code][rep_idx]
            superblocks[code].append(superblock)
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
