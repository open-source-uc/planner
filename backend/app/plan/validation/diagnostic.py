from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel


class FlatDiagnostic(BaseModel):
    course_code: Optional[str]
    is_warning: bool
    message: str


class FlatValidationResult(BaseModel):
    diagnostics: list[FlatDiagnostic]


class Diagnostic(BaseModel, ABC):
    """
    A diagnostic message, that may be associated to a course that the user is taking.
    """

    def course_code(self) -> Optional[str]:
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

    def add(self, diag: Diagnostic):
        self.diagnostics.append(diag)

    def flatten(self) -> FlatValidationResult:
        flat_diags: list[FlatDiagnostic] = []
        for diag in self.diagnostics:
            flat = FlatDiagnostic(
                course_code=diag.course_code(),
                is_warning=isinstance(diag, DiagnosticWarn),
                message=diag.message(),
            )
            flat_diags.append(flat)
        return FlatValidationResult(diagnostics=flat_diags)
