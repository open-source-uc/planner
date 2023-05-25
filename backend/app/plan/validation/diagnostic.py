from abc import ABC, abstractmethod
from typing import Optional
from ..plan import ClassId, ValidatablePlan
from pydantic import BaseModel


class FlatDiagnostic(BaseModel):
    # The course identifier is a (code, index of the instance of this code) tuple.
    class_id: Optional[ClassId]
    is_warning: bool
    message: str


class FlatValidationResult(BaseModel):
    diagnostics: list[FlatDiagnostic]
    # Associates course indices with academic block names (superblocks).
    # Used to assign colors to each course depending on what purpose they serve.
    # Ideally, this would be a `dict[str, list[Optional[str]]]`, but the typescript
    # client generator is a bit dumb and forgets about `Optional[]`???
    course_superblocks: dict[str, list[str]]


class Diagnostic(BaseModel, ABC):
    """
    A diagnostic message, that may be associated to a course that the user is taking.
    """

    def class_index(self) -> Optional[tuple[int, int]]:
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
    course_superblocks: dict[str, list[Optional[str]]]

    @staticmethod
    def empty(plan: ValidatablePlan) -> "ValidationResult":
        return ValidationResult(
            diagnostics=[],
            course_superblocks={},
        )

    def add(self, diag: Diagnostic):
        self.diagnostics.append(diag)

    def remove(self, indices: list[int]):
        for i, _diag in reversed(list(enumerate(self.diagnostics))):
            if i in indices:
                del self.diagnostics[i]

    def flatten(self, plan: ValidatablePlan) -> FlatValidationResult:
        # Build index -> id mapping
        counters: dict[str, int] = {}
        idx2id: list[list[ClassId]] = []
        for sem in plan.classes:
            ids: list[ClassId] = []
            for c in sem:
                count = counters.get(c.code, 0)
                counters[c.code] = count + 1
                ids.append(ClassId(code=c.code, instance=count))
            idx2id.append(ids)

        # Flatten diagnostics
        flat_diags: list[FlatDiagnostic] = []
        for diag in self.diagnostics:
            index = diag.class_index()
            if index is None:
                id = None
            else:
                id = idx2id[index[0]][index[1]]
            flat = FlatDiagnostic(
                class_id=id,
                is_warning=isinstance(diag, DiagnosticWarn),
                message=diag.message(),
            )
            flat_diags.append(flat)
        return FlatValidationResult(
            diagnostics=flat_diags,
            course_superblocks={
                code: [sb or "" for sb in instances]
                for code, instances in self.course_superblocks.items()
            },
        )
