from collections import defaultdict

from ....user.info import StudentContext
from ...course import PseudoCourse, pseudocourse_with_credits
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
    FilledCourse,
    SolvedCurriculum,
    TakenCourse,
    solve_curriculum,
)
from .tree import Curriculum


def _diagnose_blocks(
    courseinfo: CourseInfo,
    out: ValidationResult,
    g: SolvedCurriculum,
):
    # Avoid diagnosing a course twice if it is present in two layers
    diagnosed: defaultdict[str, set[int]] = defaultdict(set)
    equivalent_finder: EquivalentFillerFinder | None = None

    for _layer_id, layer in g.layers.items():
        for code, courses in layer.courses.items():
            for rep_idx, course in courses.items():
                if isinstance(course.origin, FilledCourse):
                    # This course was added by the solver because it could not fill
                    # enough credits with the user's courses

                    # Check if a diagnostic is necessary
                    if course.active_edge is None:
                        continue
                    if rep_idx in diagnosed[code]:
                        continue
                    diagnosed[code].add(rep_idx)

                    # Find equivalents
                    if equivalent_finder is None:
                        equivalent_finder = EquivalentFillerFinder(g)
                    raw_equivalents = equivalent_finder.find_equivalents(
                        course.active_edge,
                    )

                    # Collapse equivalents and adjust equivalence credits
                    equivalents_set: dict[str, PseudoCourse] = {
                        c.code: c for c in raw_equivalents
                    }
                    equivalents: list[PseudoCourse] = [
                        pseudocourse_with_credits(c, course.active_flow)
                        for c in equivalents_set.values()
                    ]

                    # Diagnose
                    out.add(
                        CurriculumErr(
                            block=[
                                b.name
                                for b in course.active_edge.block_path
                                if b.name is not None
                            ],
                            credits=course.active_flow,
                            recommend=equivalents,
                        ),
                    )


def _tag_superblocks(g: SolvedCurriculum, out: ValidationResult):
    for code, courses in g.layers[""].courses.items():
        for rep_idx, course in courses.items():
            if isinstance(course.origin, TakenCourse):
                # This course is a concrete course the user took

                # Find the active superblock
                superblock = ""
                if course.active_edge is not None:
                    # Use the first named block in the path
                    for block in course.active_edge.block_path:
                        if block.name is not None:
                            superblock = block.name
                            break

                # Tag it
                out.course_superblocks[code][rep_idx] = superblock


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

    # Tag each course with its associated superblock
    _tag_superblocks(g, out)

    # Count unassigned credits (including passed courses)
    # However, only emit the warning if there is at least 1 not-yet-passed unassigned
    # course
    unassigned: int = 0
    notpassed_unassigned: bool = False
    for code, instances in out.course_superblocks.items():
        for rep_idx, superblock in enumerate(instances):
            if superblock == "":
                course = g.taken.mapped[code][rep_idx]
                unassigned += courseinfo.get_credits(course.course) or 0
                if user_ctx is None or course.sem >= user_ctx.next_semester:
                    notpassed_unassigned = True
    if notpassed_unassigned:
        out.add(UnassignedWarn(unassigned_credits=unassigned))
