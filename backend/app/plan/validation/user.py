"""
Validations related to the owner of a plan.
These validations are all optional and should be more "informative" than "normative",
since guests (with no associated user context) can also validate plans.
"""


from typing import Optional
from .curriculum.tree import CurriculumSpec
from .diagnostic import (
    MismatchedCurriculumSelectionWarn,
    ValidationResult,
    MismatchedCyearErr,
)
from ...user.info import StudentContext
from ..plan import ValidatablePlan


def _is_mismatched(selected: Optional[str], reported: Optional[str]):
    return reported is not None and selected is not None and reported != selected


def validate_against_owner(
    plan: ValidatablePlan, user_ctx: StudentContext, out: ValidationResult
):
    if str(plan.curriculum.cyear) != user_ctx.info.cyear:
        out.add(
            MismatchedCyearErr(plan=plan.curriculum.cyear, user=user_ctx.info.cyear)
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
            )
        )
