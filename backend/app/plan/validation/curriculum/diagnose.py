from collections import defaultdict
from dataclasses import dataclass, field

from ....user.info import StudentContext
from ...course import ConcreteId, EquivalenceId, PseudoCourse
from ...courseinfo import CourseInfo
from ...plan import ValidatablePlan
from ..diagnostic import (
    CurriculumErr,
    NoMajorMinorWarn,
    UnassignedWarn,
    ValidationResult,
)
from .solve import (
    EquivalentFillerFinder,
    SolvedCurriculum,
    solve_curriculum,
)
from .tree import Curriculum


@dataclass
class MissingCourse:
    credits: int = 0
    blocks: list[list[str]] = field(default_factory=list)
    fillers: set[str] = field(default_factory=set)


def _diagnose_blocks(
    courseinfo: CourseInfo,
    out: ValidationResult,
    g: SolvedCurriculum,
):
    equivalent_finder: EquivalentFillerFinder | None = None

    # Extract the amount of credits missing and which blocks require it
    missing: defaultdict[str, MissingCourse] = defaultdict(MissingCourse)
    for layer in g.layers.values():
        for code, layercourse in layer.courses.items():
            # Check if this course code is missing some credits
            total_missing = 0
            for block_edge in layercourse.block_edges:
                if block_edge.filler_flow > 0:
                    # This course-block edge is missing credits!
                    # It is missing exactly filler_flow credits
                    total_missing += block_edge.filler_flow
                    # Mark this block as lacking
                    missing[code].blocks.append(
                        [b.name for b in block_edge.block_path if b.name is not None],
                    )
                    # Find which courses could be used to supply this block
                    if equivalent_finder is None:
                        equivalent_finder = EquivalentFillerFinder(g)
                    missing[code].fillers |= equivalent_finder.find_equivalents(
                        block_edge,
                    )
            if total_missing > 0:
                missing[code].credits = max(missing[code].credits, total_missing)

    # Diagnose using the missing set of codes
    for miss in missing.values():
        # Adjust filler credits and fetch names
        fillers: list[PseudoCourse] = []
        for filler_code in miss.fillers:
            info = courseinfo.try_equiv(filler_code)
            if info is not None:
                fillers.append(EquivalenceId(code=filler_code, credits=miss.credits))
            else:
                fillers.append(ConcreteId(code=filler_code))

        # Create diagnostic
        out.add(
            CurriculumErr(
                blocks=miss.blocks,
                credits=miss.credits,
                recommend=fillers,
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
