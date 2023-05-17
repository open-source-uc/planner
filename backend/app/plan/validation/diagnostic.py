from abc import ABC, abstractmethod
from typing import Optional
from ..plan import ClassIndex, ValidatablePlan
from pydantic import BaseModel


class FlatDiagnostic(BaseModel):
    # The course index is a (semester, position within semester) tuple.
    course_index: Optional[ClassIndex]
    is_warning: bool
    message: str


class FlatValidationResult(BaseModel):
    diagnostics: list[FlatDiagnostic]
    # Associates course indices with academic block names (superblocks).
    # Used to assign colors to each course depending on what purpose they serve.
    # Ideally, this would be a `list[list[Optional[str]]]`, but the typescript client
    # generator is a bit dumb and forgets about `Optional[]`???
    course_superblocks: list[list[str]]


class Diagnostic(BaseModel, ABC):
    """
    A diagnostic message, that may be associated to a course that the user is taking.
    """

    def course_index(self) -> Optional[ClassIndex]:
        return None

    @abstractmethod
    def message(self) -> str:
        pass


class DiagnosticErr(Diagnostic):
    pass


class DiagnosticWarn(Diagnostic):
    pass


class ValidationResult(BaseModel):
    """
    Simply a list of diagnostics, in the same order that is shown to the user.
    """

    diagnostics: list[Diagnostic]
    # Associates course indices with academic block names (superblocks).
    # Used to assign colors to each course depending on what purpose they serve.
    course_superblocks: list[list[Optional[str]]]

    @staticmethod
    def empty(plan: ValidatablePlan) -> "ValidationResult":
        return ValidationResult(
            diagnostics=[],
            course_superblocks=[[None for _c in sem] for sem in plan.classes],
        )

    def add(self, diag: Diagnostic):
        self.diagnostics.append(diag)

    def remove(self, indices: list[int]):
        for i, _diag in reversed(list(enumerate(self.diagnostics))):
            if i in indices:
                del self.diagnostics[i]

    def flatten(self) -> FlatValidationResult:
        flat_diags: list[FlatDiagnostic] = []
        for diag in self.diagnostics:
            flat = FlatDiagnostic(
                course_index=diag.course_index(),
                is_warning=isinstance(diag, DiagnosticWarn),
                message=diag.message(),
            )
            flat_diags.append(flat)
        return FlatValidationResult(
            diagnostics=flat_diags,
            course_superblocks=[
                [sb or "" for sb in sem] for sem in self.course_superblocks
            ],
        )
