"""
Validations related to the owner of a plan.
These validations are all optional and should be more "informative" than "normative",
since guests (with no associated user context) can also validate plans.
"""


from typing import Optional
from .curriculum.tree import Cyear
from .diagnostic import DiagnosticErr, DiagnosticWarn, ValidationResult
from ...user.info import StudentContext
from ..plan import ValidatablePlan


class MismatchedCyearErr(DiagnosticErr):
    plan: Cyear
    user: str

    def message(self) -> str:
        return (
            f"Este plan esta configurado para el curriculum {self.plan}, pero segun "
            + f"tu año de ingreso te corresponde {self.user}"
        )


class MismatchedCurriculumSelectionWarn(DiagnosticWarn):
    wrong_major: bool
    wrong_minor: bool
    wrong_title: bool

    def message(self) -> str:
        missing: list[str] = []
        if self.wrong_major:
            missing.append("major")
        if self.wrong_minor:
            missing.append("minor")
        if self.wrong_title:
            missing.append("título")
        missing_str = ""
        for i in range(len(missing)):
            if i > 0:
                if i == len(missing) - 1:
                    missing_str += " y "
                else:
                    missing_str += ", "
            missing_str += missing[i]
        return f"El {missing_str} elegido no es el que tienes inscrito oficialmente"


def _is_mismatched(selected: Optional[str], reported: Optional[str]):
    return reported is not None and selected is not None and reported != selected


def validate_against_owner(
    plan: ValidatablePlan, user_ctx: StudentContext, out: ValidationResult
):
    if str(plan.curriculum.cyear) != user_ctx.info.cyear:
        out.add(
            MismatchedCyearErr(plan=plan.curriculum.cyear, user=user_ctx.info.cyear)
        )

    mismatch = MismatchedCurriculumSelectionWarn(
        wrong_major=_is_mismatched(plan.curriculum.major, user_ctx.info.reported_major),
        wrong_minor=_is_mismatched(plan.curriculum.minor, user_ctx.info.reported_minor),
        wrong_title=(
            plan.curriculum.title is None and user_ctx.info.reported_title is not None
        )
        or _is_mismatched(plan.curriculum.title, user_ctx.info.reported_title),
    )
    if mismatch.wrong_major or mismatch.wrong_minor or mismatch.wrong_title:
        out.add(mismatch)
