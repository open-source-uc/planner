from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from ..course import PseudoCourse
from ..plan import ClassId, ValidatablePlan
from .courses.logic import Expr
from .curriculum.tree import CurriculumSpec, Cyear


class BaseDiagnostic(BaseModel):
    # Determines the kind of diagnostic.
    kind: str
    # Associated to either a set of courses, or a set of semesters.
    associated_to: list[ClassId] | list[int] | None
    # Either a warning or an error.
    is_err: bool


class DiagnosticErr(BaseDiagnostic):
    is_err: Literal[True] = Field(True, const=True)


class DiagnosticWarn(BaseDiagnostic):
    is_err: Literal[False] = Field(False, const=True)


class CourseRequirementErr(DiagnosticErr):
    """
    Indicates that a course (`associated_to`) is missing some requirements (`missing`).
    """

    kind: Literal["req"] = Field("req", const=True)
    associated_to: list[ClassId]
    missing: Expr
    modernized_missing: Expr


class UnknownCourseErr(DiagnosticErr):
    """
    Indicates that some courses (`associated_to`) have unknown/invalid codes.
    """

    kind: Literal["unknown"] = Field("unknown", const=True)
    associated_to: list[ClassId]


class MismatchedCyearErr(DiagnosticErr):
    """
    Indicates that the plan is validating for a cyear (`plan`) that does not match the
    user's cyear (`user`).
    """

    kind: Literal["cyear"] = Field("cyear", const=True)
    associated_to: None = None
    plan: Cyear
    user: str


class MismatchedCurriculumSelectionWarn(DiagnosticWarn):
    """
    Indicates that the plan selection of curriculum does not match the official
    curriculum declaration.
    """

    kind: Literal["currdecl"] = Field("currdecl", const=True)
    associated_to: None = None
    plan: CurriculumSpec
    user: CurriculumSpec


class OutdatedPlanErr(DiagnosticErr):
    """
    Indicates that the plan does not reflect the courses that the user has taken.
    This could happen if the user planned ahead, but didn't follow their plan.
    Afterwards, when they take different courses than they planned, their plan becomes
    outdated.
    The semesters that are mismatched are included in `associated_to`.
    """

    kind: Literal["outdated"] = Field("outdated", const=True)
    associated_to: list[int]


class OutdatedCurrentSemesterErr(DiagnosticErr):
    """
    Indicates that the current semester in the plan does not reflect the courses that
    the user is currently taken.
    This could be because the user is experimenting with modifying their current
    semester (ie. removing courses that they don't expect to pass).
    This is the "smaller version" of `OutdatedPlanErr`.
    """

    kind: Literal["outdatedcurrent"] = Field("outdatedcurrent", const=True)
    associated_to: list[int]


class SemestralityWarn(DiagnosticWarn):
    """
    Indicates that some courses (`associated_to`) are not normally given in the
    semester they are in.
    Instead, they are usually only given in semesters with parity `only_available_on`.
    """

    kind: Literal["sem"] = Field("sem", const=True)
    associated_to: list[ClassId]
    only_available_on: int


class UnavailableCourseWarn(DiagnosticWarn):
    """
    Indicates that some courses (`associated_to`) have not been given in a long while
    and are probably unavailable.
    """

    kind: Literal["unavail"] = Field("unavail", const=True)
    associated_to: list[ClassId]


class AmbiguousCourseErr(DiagnosticErr):
    """
    Indicates that some equivalences (`associated_to`) should be disambiguated and they
    aren't.
    """

    kind: Literal["equiv"] = Field("equiv", const=True)
    associated_to: list[ClassId]


class SemesterCreditsWarn(DiagnosticWarn):
    """
    Indicates that some semesters (`associated_to`) have more than the recommended
    amount of credits.
    """

    kind: Literal["creditswarn"] = Field("creditswarn", const=True)
    associated_to: list[int]
    max_recommended: int
    actual: int


class SemesterCreditsErr(DiagnosticErr):
    """
    Indicates that some semesters (`associated_to`) have more than the allowed amount
    of credits.
    """

    kind: Literal["creditserr"] = Field("creditserr", const=True)
    associated_to: list[int]
    max_allowed: int
    actual: int


class CurriculumErr(DiagnosticErr):
    """
    Indicates that there are some courses missing to fulfill the chosen curriculum.
    The incomplete block is given in `block`, and the amount of credits missing in
    `credits`.
    A set of courses that would fill this block (possibly equivalences) is given in
    `recommend`.
    """

    kind: Literal["curr"] = Field("curr", const=True)
    associated_to: None = None
    block: str
    credits: int
    recommend: list[PseudoCourse]


class UnassignedWarn(DiagnosticWarn):
    """
    Indicates that some courses (in total `unassigned_credits` credits) have no use in
    the curriculum.
    """

    kind: Literal["useless"] = Field("useless", const=True)
    associated_to: None = None
    unassigned_credits: int


class NoMajorMinorWarn(DiagnosticWarn):
    """
    Indicates that no major or minor is chosen, and it should be chosen to validate the
    plan correctly.
    """

    kind: Literal["nomajor"] = Field("nomajor", const=True)
    associated_to: None = None
    plan: CurriculumSpec


Diagnostic = Annotated[
    Union[
        CourseRequirementErr,
        UnknownCourseErr,
        MismatchedCyearErr,
        MismatchedCurriculumSelectionWarn,
        OutdatedPlanErr,
        OutdatedCurrentSemesterErr,
        SemestralityWarn,
        UnavailableCourseWarn,
        AmbiguousCourseErr,
        SemesterCreditsWarn,
        SemesterCreditsErr,
        CurriculumErr,
        UnassignedWarn,
        NoMajorMinorWarn,
    ],
    Field(discriminator="kind"),
]


class ValidationResult(BaseModel):
    diagnostics: list[Diagnostic]
    course_superblocks: dict[str, list[str]]

    @staticmethod
    def empty(plan: ValidatablePlan) -> "ValidationResult":
        blocks: dict[str, list[str]] = {}
        for sem in plan.classes:
            for c in sem:
                if c.code not in blocks:
                    blocks[c.code] = []
                blocks[c.code].append("")
        return ValidationResult(diagnostics=[], course_superblocks=blocks)

    def add(self, diag: Diagnostic):
        self.diagnostics.append(diag)
