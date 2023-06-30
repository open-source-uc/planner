from typing import Annotated, Literal

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
    is_err: Literal[True] = Field(default=True, const=True)


class DiagnosticWarn(BaseDiagnostic):
    is_err: Literal[False] = Field(default=False, const=True)


class CourseRequirementErr(DiagnosticErr):
    """
    Indicates that a course (`associated_to`) is missing some requirements (`missing`).

    - `missing`: The raw missing requirements, as specified in the course requirements.
        This expression is simplified, and only contains the courses that are actually
        missing.
    - `missing_modernized`: Like `missing`, but course codes are replaced by their
        modernized counterparts.
    - `push_back`: If the `associated_to` course can be moved back some semesters an
        then fulfill the requirements, this property is the index of that semester.
    - `pull_forward`: If some requirements already exist in the plan but they are too
        late to count as requirements for the `associate_to` course, they are listed
        here, along with the semester that they would have to be moved to.
    - `add_absent`: Requirements that are not in the plan and have to be added.
        The modernized code is listed here.
    """

    kind: Literal["req"] = Field(default="req", const=True)
    associated_to: list[ClassId]
    missing: Expr
    modernized_missing: Expr
    push_back: int | None
    pull_forward: dict[str, int]
    add_absent: dict[str, int]


class UnknownCourseErr(DiagnosticErr):
    """
    Indicates that some courses (`associated_to`) have unknown/invalid codes.
    """

    kind: Literal["unknown"] = Field(default="unknown", const=True)
    associated_to: list[ClassId]


class MismatchedCyearErr(DiagnosticErr):
    """
    Indicates that the plan is validating for a cyear (`plan`) that does not match the
    user's cyear (`user`).
    """

    kind: Literal["cyear"] = Field(default="cyear", const=True)
    associated_to: None = None
    plan: Cyear
    user: str


class MismatchedCurriculumSelectionWarn(DiagnosticWarn):
    """
    Indicates that the plan selection of curriculum does not match the official
    curriculum declaration.
    """

    kind: Literal["currdecl"] = Field(default="currdecl", const=True)
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

    kind: Literal["outdated"] = Field(default="outdated", const=True)
    associated_to: list[int]


class OutdatedCurrentSemesterErr(DiagnosticErr):
    """
    Indicates that the current semester in the plan does not reflect the courses that
    the user is currently taken.
    This could be because the user is experimenting with modifying their current
    semester (ie. removing courses that they don't expect to pass).
    This is the "smaller version" of `OutdatedPlanErr`.
    """

    kind: Literal["outdatedcurrent"] = Field(default="outdatedcurrent", const=True)
    associated_to: list[int]


class SemestralityWarn(DiagnosticWarn):
    """
    Indicates that some courses (`associated_to`) are not normally given in the
    semester they are in.
    Instead, they are usually only given in semesters with parity `only_available_on`.
    """

    kind: Literal["sem"] = Field(default="sem", const=True)
    associated_to: list[ClassId]
    only_available_on: int


class UnavailableCourseWarn(DiagnosticWarn):
    """
    Indicates that some courses (`associated_to`) have not been given in a long while
    and are probably unavailable.
    """

    kind: Literal["unavail"] = Field(default="unavail", const=True)
    associated_to: list[ClassId]


class AmbiguousCourseErr(DiagnosticErr):
    """
    Indicates that some equivalences (`associated_to`) should be disambiguated and they
    aren't.
    """

    kind: Literal["equiv"] = Field(default="equiv", const=True)
    associated_to: list[ClassId]


class SemesterCreditsWarn(DiagnosticWarn):
    """
    Indicates that some semesters (`associated_to`) have more than the recommended
    amount of credits.
    """

    kind: Literal["creditswarn"] = Field(default="creditswarn", const=True)
    associated_to: list[int]
    max_recommended: int
    actual: int


class SemesterCreditsErr(DiagnosticErr):
    """
    Indicates that some semesters (`associated_to`) have more than the allowed amount
    of credits.
    """

    kind: Literal["creditserr"] = Field(default="creditserr", const=True)
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
    Because equivalences could be potentially unknown to the frontend and we don't want
    to show the user equivalence codes, each course is coupled with its name.
    """

    kind: Literal["curr"] = Field(default="curr", const=True)
    associated_to: None = None
    block: list[str]
    credits: int
    recommend: list[tuple[PseudoCourse, str]]


class UnassignedWarn(DiagnosticWarn):
    """
    Indicates that some courses (in total `unassigned_credits` credits) have no use in
    the curriculum.
    """

    kind: Literal["useless"] = Field(default="useless", const=True)
    associated_to: None = None
    unassigned_credits: int


class NoMajorMinorWarn(DiagnosticWarn):
    """
    Indicates that no major or minor is chosen, and it should be chosen to validate the
    plan correctly.
    """

    kind: Literal["nomajor"] = Field(default="nomajor", const=True)
    associated_to: None = None
    plan: CurriculumSpec


Diagnostic = Annotated[
    CourseRequirementErr
    | UnknownCourseErr
    | MismatchedCyearErr
    | MismatchedCurriculumSelectionWarn
    | OutdatedPlanErr
    | OutdatedCurrentSemesterErr
    | SemestralityWarn
    | UnavailableCourseWarn
    | AmbiguousCourseErr
    | SemesterCreditsWarn
    | SemesterCreditsErr
    | CurriculumErr
    | UnassignedWarn
    | NoMajorMinorWarn,
    Field(discriminator="kind"),
]


class ValidationResult(BaseModel):
    diagnostics: list[Diagnostic]
    course_superblocks: dict[str, list[str]]

    @staticmethod
    def empty(plan: ValidatablePlan) -> "ValidationResult":
        return ValidationResult(diagnostics=[], course_superblocks={})

    def add(self, diag: Diagnostic):
        self.diagnostics.append(diag)
