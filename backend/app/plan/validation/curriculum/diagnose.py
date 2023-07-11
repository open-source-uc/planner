from collections import defaultdict

from ....user.info import StudentContext
from ...course import PseudoCourse
from ...courseinfo import CourseInfo
from ...plan import ValidatablePlan
from ..diagnostic import (
    CurriculumErr,
    NoMajorMinorWarn,
    UnassignedWarn,
    ValidationResult,
)
from .solve import (
    SolvedCurriculum,
    extract_filler_groups,
    solve_curriculum,
)
from .tree import Curriculum


def _diagnose_blocks(
    courseinfo: CourseInfo,
    out: ValidationResult,
    g: SolvedCurriculum,
):
    def fetch_name(filler: PseudoCourse):
        info = courseinfo.try_any(filler)
        return (filler, "?" if info is None else info.name)

    # Check which curriculum blocks are incomplete, report that they are missing and
    # suggest fillers for it
    for filler_group in extract_filler_groups(g):
        # Deduplicate filler courses with the same code
        by_code: dict[str, PseudoCourse] = {
            filler.course.code: filler.course
            for filler in filler_group.fillers.values()
        }

        out.add(
            CurriculumErr(
                blocks=[
                    [block.name for block in block_path if block.name]
                    for block_path in filler_group.blocks.values()
                ],
                credits=filler_group.credits,
                fill_options=[
                    fetch_name(filler)
                    for filler in by_code.values()
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
    g = solve_curriculum(courseinfo, curriculum, plan.classes)

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
            mapped = g.map_class_id(course.code, rep_idx)
            if mapped is not None:
                superblock = g.superblocks[mapped[0]][mapped[1]]
                if superblock == "":
                    unassigned += courseinfo.get_credits(course) or 0
                    if sem_i >= first_unvalidated_sem:
                        unassigned_notpassed = True
    if unassigned_notpassed:
        out.add(UnassignedWarn(unassigned_credits=unassigned))

    # Tag each course with its associated superblock
    superblocks = {}
    for code, count in rep_counter.items():
        superblocks[code] = ["" for _ in range(count)]
        for rep_idx in range(count):
            mapped = g.map_class_id(code, rep_idx)
            if mapped is not None:
                superblocks[code][rep_idx] = g.superblocks[mapped[0]][mapped[1]]
    out.course_superblocks = superblocks
