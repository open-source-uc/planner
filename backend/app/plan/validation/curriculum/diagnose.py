from collections import defaultdict

from fastapi import HTTPException

from app.plan.course import EquivalenceId, PseudoCourse
from app.plan.courseinfo import CourseInfo
from app.plan.plan import ClassId, ValidatablePlan
from app.plan.validation.curriculum.solve import (
    SolvedCurriculum,
    solve_curriculum,
)
from app.plan.validation.curriculum.tree import Curriculum
from app.plan.validation.diagnostic import (
    CurriculumErr,
    NoMajorMinorWarn,
    RecolorWarn,
    UnassignedWarn,
    ValidationResult,
)
from app.user.info import StudentInfo


def _check_missing_fillers(
    out: ValidationResult,
    g: SolvedCurriculum,
    panacea_recolors: list[tuple[ClassId, EquivalenceId]] | None,
) -> bool:
    """
    Check if `g` indicates that fillers should be added, and if so add a `CurriculumErr`
    to `out`.
    Note that `g` might be allowing or forbiding recolors, this function does not care.

    `panacea_recolors` is an optional argument that is passed on directly to any
    generated `CurriculumErr`.
    It indicates that recoloring in this way will solve all curriculum colors.

    Returns whether the curriculum is satisfied (ie. if there are no fillers missing).
    """

    satisfied = True

    for usable in g.usable.values():
        for inst in usable.instances:
            if not inst.filler or not inst.flow:
                continue

            options: list[list[PseudoCourse]] = g.find_swapouts(inst)

            # This filler is active, therefore something is missing
            satisfied = False
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
                    fill_options=[filler for option in options for filler in option],
                    panacea_recolor_courses=[id for id, _ in panacea_recolors]
                    if panacea_recolors
                    else None,
                    panacea_recolor_blocks=[equiv for _, equiv in panacea_recolors]
                    if panacea_recolors
                    else None,
                ),
            )

    return satisfied


def _diagnose_blocks(
    courseinfo: CourseInfo,
    out: ValidationResult,
    g: SolvedCurriculum,
):
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
    satisfied_with_recoloring = _check_missing_fillers(out, g, None)

    if satisfied_with_recoloring:
        # There are enough courses to satisfy the curriculum, but they might not be
        # the correct colors
        # Now, forbid recoloring and retry
        if g.forbid_recolor():
            # Reassigning equivalences can save us some courses

            # The user might prefer to keep these colors and add more courses (ie. if
            # they are in the middle of changing their curriculum), but they might also
            # want to just change the colors and solve the problem.
            # Give them both options
            satisfied_without_recoloring = _check_missing_fillers(out, g, recolors)
            if satisfied_without_recoloring:
                # All is OK, but remember that `forbid_recolor` returned true!
                # Therefore, we could save some courses by recoloring
                # Let the user know that
                out.add(
                    RecolorWarn(
                        associated_to=[id for id, _equiv in recolors],
                        recolor_as=[equiv for _id, equiv in recolors],
                    ),
                )
            else:
                # The curriculum is satisfied with recoloring, but not without it
                # An error was emitted inside of `_check_missing_fillers`, so there's
                # nothing to do here
                pass
        else:
            # All is OK!
            pass
    else:
        # There are not even enough courses to satisfy the curriculum _with
        # recoloring_.
        # Let the user solve that issue first, then worry about the right colors.
        pass


def diagnose_curriculum(
    courseinfo: CourseInfo,
    curriculum: Curriculum,
    plan: ValidatablePlan,
    user_ctx: StudentInfo | None,
    out: ValidationResult,
):
    # Produce a warning if no major/minor is selected
    if plan.curriculum.major is None or plan.curriculum.minor is None:
        out.add(NoMajorMinorWarn(plan=plan.curriculum))

    # Solve plan
    g = solve_curriculum(
        courseinfo,
        plan.curriculum,
        curriculum,
        plan.classes,
        user_ctx.current_semester if user_ctx else 0,
    )

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
