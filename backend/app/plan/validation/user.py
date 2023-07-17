"""
Validations related to the owner of a plan.
These validations are all optional and should be more "informative" than "normative",
since guests (with no associated user context) can also validate plans.
"""


from ...user.info import StudentContext
from ..course import EquivalenceId, PseudoCourse
from ..plan import ValidatablePlan
from .curriculum.tree import CurriculumSpec
from .diagnostic import (
    MismatchedCurriculumSelectionWarn,
    MismatchedCyearErr,
    OutdatedCurrentSemesterErr,
    OutdatedPlanErr,
    ValidationResult,
)


def _check_sem_eq(sem1: list[PseudoCourse], sem2: list[PseudoCourse]) -> bool:
    # Important not to modify the original `sem1` and `sem2` lists here
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
    plan: ValidatablePlan,
    user_ctx: StudentContext,
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
        if len(unsynced_sems) == 1 and unsynced_sems[0] == user_ctx.current_semester:
            out.add(OutdatedCurrentSemesterErr(associated_to=unsynced_sems))
        else:
            out.add(OutdatedPlanErr(associated_to=unsynced_sems))


def _is_mismatched(selected: str | None, reported: str | None):
    return (
        reported is not None
        and selected is not None
        and not selected.startswith(reported)
    )


def validate_against_owner(
    plan: ValidatablePlan,
    user_ctx: StudentContext,
    out: ValidationResult,
):
    if str(plan.curriculum.cyear) != user_ctx.info.cyear:
        out.add(
            MismatchedCyearErr(plan=plan.curriculum.cyear, user=user_ctx.info.cyear),
        )

    if (
        _is_mismatched(plan.curriculum.major, user_ctx.info.reported_major)
        or _is_mismatched(plan.curriculum.minor, user_ctx.info.reported_minor)
        or _is_mismatched(plan.curriculum.title, user_ctx.info.reported_title)
        or (plan.curriculum.title is None and user_ctx.info.reported_title is not None)
    ):
        out.add(
            MismatchedCurriculumSelectionWarn(
                plan=plan.curriculum,
                user=CurriculumSpec(
                    cyear=plan.curriculum.cyear,
                    major=user_ctx.info.reported_major,
                    minor=user_ctx.info.reported_minor,
                    title=user_ctx.info.reported_title,
                ),
            ),
        )

    _validate_possibly_outdated(plan, user_ctx, out)
