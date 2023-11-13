from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.plan.course import EquivalenceId, PseudoCourse
from app.plan.plan import ClassId, ValidatablePlan
from app.plan.validation.courses.logic import Expr
from app.plan.validation.curriculum.tree import CurriculumSpec, Cyear


class CourseRequirementErr(BaseModel):
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

    is_err: Literal[True] = Field(default=True, const=True)
    kind: Literal["req"] = Field(default="req", const=True)
    associated_to: list[ClassId]

    missing: Expr
    modernized_missing: Expr
    push_back: int | None
    pull_forward: dict[str, int]
    add_absent: dict[str, int]


class UnknownCourseErr(BaseModel):
    """
    Indicates that some courses (`associated_to`) have unknown/invalid codes.
    """

    is_err: Literal[True] = Field(default=True, const=True)
    kind: Literal["unknown"] = Field(default="unknown", const=True)
    associated_to: list[ClassId]


class MismatchedCyearErr(BaseModel):
    """
    Indicates that the plan is validating for a cyear (`plan`) that does not match the
    user's cyear (`user`).
    """

    is_err: Literal[True] = Field(default=True, const=True)
    kind: Literal["cyear"] = Field(default="cyear", const=True)
    associated_to: None = None

    plan: Cyear
    user: str


class MismatchedCurriculumSelectionWarn(BaseModel):
    """
    Indicates that the plan selection of curriculum does not match the official
    curriculum declaration.
    """

    is_err: Literal[False] = Field(default=False, const=True)
    kind: Literal["currdecl"] = Field(default="currdecl", const=True)
    associated_to: None = None

    plan: CurriculumSpec
    user: CurriculumSpec


class OutdatedPlanErr(BaseModel):
    """
    Indicates that the plan does not reflect the courses that the user has taken.
    This could happen if the user planned ahead, but didn't follow their plan.
    Afterwards, when they take different courses than they planned, their plan becomes
    outdated.
    The semesters that are mismatched are included in `associated_to`.
    Each mismatched semester contains an associated entry in `replace_with` with the
    courses that should replace this semester.
    If `is_current` is true, then the only outdated semester is the current semester,
    which may be a special case if the user is trying out changes to their current
    semester.
    """

    is_err: Literal[True] = Field(default=True, const=True)
    kind: Literal["outdated"] = Field(default="outdated", const=True)
    associated_to: list[int]

    replace_with: list[list[PseudoCourse]]
    is_current: bool


class SemestralityWarn(BaseModel):
    """
    Indicates that some courses (`associated_to`) are not normally given in the
    semester they are in.
    Instead, they are usually only given in semesters with parity `only_available_on`.
    """

    is_err: Literal[False] = Field(default=False, const=True)
    kind: Literal["sem"] = Field(default="sem", const=True)
    associated_to: list[ClassId]

    only_available_on: int


class UnavailableCourseWarn(BaseModel):
    """
    Indicates that some courses (`associated_to`) have not been given in a long while
    and are probably unavailable.
    """

    is_err: Literal[False] = Field(default=False, const=True)
    kind: Literal["unavail"] = Field(default="unavail", const=True)
    associated_to: list[ClassId]


class AmbiguousCourseErr(BaseModel):
    """
    Indicates that some equivalences (`associated_to`) should be disambiguated and they
    aren't.
    """

    is_err: Literal[True] = Field(default=True, const=True)
    kind: Literal["equiv"] = Field(default="equiv", const=True)
    associated_to: list[ClassId]


class SemesterCreditsDiag(BaseModel):
    """
    Indicates that some semesters (`associated_to`) have more than the recommended or
    allowed amount of credits.

    If `is_err` is `True`, the hard limit was surpassed.
    If `is_err` is `False`, only the soft limit was surpassed.
    """

    is_err: bool
    kind: Literal["credits"] = Field(default="credits", const=True)
    associated_to: list[int]

    credit_limit: int
    actual: int


class RecolorDiag(BaseModel):
    """
    Indicates that reassigning the equivalences that are attached to the courses could
    save some unnecessary classes.
    Reassigning the attached equivalences is informally referred to as "recoloring".

    `recolor_as` has the same length as `associated_to`, and indicated which
    equivalence should be assigned to which course, respectively.
    """

    is_err: bool
    kind: Literal["recolor"] = Field(default="recolor", const=True)
    associated_to: list[ClassId]

    recolor_as: list[EquivalenceId]


class CurriculumErr(BaseModel):
    """
    Indicates that there are some courses missing to fulfill the chosen curriculum.
    The incomplete block is given in `block`, and the amount of credits missing in
    `credits`.
    A set of courses that would fill this block (possibly equivalences) is given in
    `recommend`.
    Because equivalences could be potentially unknown to the frontend and we don't want
    to show the user equivalence codes, each course is coupled with its name.
    """

    is_err: Literal[True] = Field(default=True, const=True)
    kind: Literal["curr"] = Field(default="curr", const=True)
    associated_to: None = None

    blocks: list[list[str]]
    credits: int
    fill_options: list[tuple[PseudoCourse, str]]


class UnassignedWarn(BaseModel):
    """
    Indicates that some courses (in total `unassigned_credits` credits) have no use in
    the curriculum.
    """

    is_err: Literal[False] = Field(default=False, const=True)
    kind: Literal["useless"] = Field(default="useless", const=True)
    associated_to: None = None

    unassigned_credits: int


class NoMajorMinorWarn(BaseModel):
    """
    Indicates that no major or minor is chosen, and it should be chosen to validate the
    plan correctly.
    """

    is_err: Literal[False] = Field(default=False, const=True)
    kind: Literal["nomajor"] = Field(default="nomajor", const=True)
    associated_to: None = None

    plan: CurriculumSpec


Diagnostic = Annotated[
    CourseRequirementErr
    | UnknownCourseErr
    | MismatchedCyearErr
    | MismatchedCurriculumSelectionWarn
    | OutdatedPlanErr
    | SemestralityWarn
    | UnavailableCourseWarn
    | AmbiguousCourseErr
    | SemesterCreditsDiag
    | RecolorDiag
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
