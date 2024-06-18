"""
Validations related to the owner of a plan.
These validations are all optional and should be more "informative" than "normative",
since guests (with no associated user context) can also validate plans.
"""

from app.plan.course import EquivalenceId, PseudoCourse, pseudocourse_with_equivalence
from app.plan.courseinfo import CourseInfo
from app.plan.plan import ValidatablePlan
from app.plan.validation.curriculum.solve import solve_curriculum
from app.plan.validation.curriculum.tree import Curriculum, CurriculumSpec, Leaf
from app.plan.validation.diagnostic import (
    MismatchedCurriculumSelectionWarn,
    MismatchedCyearErr,
    OutdatedPlanErr,
    ValidationResult,
)
from app.user.info import StudentInfo


def _check_sem_eq(sem1: list[PseudoCourse], sem2: list[PseudoCourse]) -> bool:
    # It is important not to modify the original `sem1` and `sem2` lists here
    sem1 = sorted(sem1, key=lambda c: c.code)
    sem2 = sorted(sem2, key=lambda c: c.code)
    if len(sem1) != len(sem2):
        return False
    for c1, c2 in zip(sem1, sem2, strict=True):
        if (
            isinstance(c1, EquivalenceId)
            or isinstance(c2, EquivalenceId)
            or c1.code != c2.code
        ):
            return False
    return True


def _validate_possibly_outdated(
    courseinfo: CourseInfo,
    curriculum: Curriculum,
    plan: ValidatablePlan,
    user_ctx: StudentInfo,
    out: ValidationResult,
):
    """
    Check whether the plan is in sync with the courses that `user_ctx` has passed.
    """

    unsynced_sems: list[int] = []
    for sem_i in range(user_ctx.next_semester):
        if not _check_sem_eq(plan.classes[sem_i], user_ctx.passed_courses[sem_i]):
            unsynced_sems.append(sem_i)
    if unsynced_sems:
        # Figure out what blocks to assign to the passed courses
        fixed_plan = plan.classes.copy()
        for sem_i in unsynced_sems:
            fixed_plan[sem_i] = user_ctx.passed_courses[sem_i].copy()
        g = solve_curriculum(
            courseinfo,
            plan.curriculum,
            curriculum,
            fixed_plan,
            user_ctx.current_semester,
        )
        for usable in g.usable.values():
            for inst in usable.instances:
                if not inst.semester_and_index:
                    continue
                sem, idx = inst.semester_and_index
                if sem in unsynced_sems:
                    attached_equiv = None
                    block_edges = inst.layers.get("")
                    if block_edges and block_edges.active_edge:
                        block = block_edges.active_edge.block_path[-1]
                        assert isinstance(block, Leaf)
                        attached_equiv = EquivalenceId(
                            code=block.list_code,
                            credits=block_edges.active_edge.flow,
                        )

                    fixed_plan[sem][idx] = pseudocourse_with_equivalence(
                        inst.original_pseudocourse,
                        attached_equiv,
                    )
        replace_with = [fixed_plan[sem] for sem in unsynced_sems]

        # Create the warning along with the fixed semesters
        out.add(
            OutdatedPlanErr(
                associated_to=unsynced_sems,
                replace_with=replace_with,
                is_current=(
                    len(unsynced_sems) == 1
                    and unsynced_sems[0] == user_ctx.current_semester
                ),
            ),
        )


def _is_mismatched(selected: str | None, reported: str | None):
    return (
        reported is not None
        and selected is not None
        and not selected.startswith(reported)
    )


def validate_against_owner(
    courseinfo: CourseInfo,
    curr: Curriculum,
    plan: ValidatablePlan,
    user_ctx: StudentInfo,
    out: ValidationResult,
):
    if plan.curriculum.cyear != user_ctx.cyear:
        out.add(
            MismatchedCyearErr(plan=plan.curriculum.cyear, user=user_ctx.cyear),
        )

    if (
        _is_mismatched(plan.curriculum.major, user_ctx.reported_major)
        or _is_mismatched(plan.curriculum.minor, user_ctx.reported_minor)
        or _is_mismatched(plan.curriculum.title, user_ctx.reported_title)
        or (plan.curriculum.title is None and user_ctx.reported_title is not None)
    ):
        out.add(
            MismatchedCurriculumSelectionWarn(
                plan=plan.curriculum,
                user=CurriculumSpec(
                    cyear=plan.curriculum.cyear,
                    major=user_ctx.reported_major,
                    minor=user_ctx.reported_minor,
                    title=user_ctx.reported_title,
                ),
            ),
        )

    _validate_possibly_outdated(courseinfo, curr, plan, user_ctx, out)
