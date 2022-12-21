from typing import Optional
from pydantic import BaseModel


class Diagnostic(BaseModel):
    """
    A diagnostic message, that may be associated to a course that the user is taking.
    """

    course_code: Optional[str]
    is_warning: bool
    message: str

    @staticmethod
    def err(msg: str, code: Optional[str] = None):
        return Diagnostic(course_code=code, is_warning=False, message=msg)

    @staticmethod
    def warn(msg: str, code: Optional[str] = None):
        return Diagnostic(course_code=code, is_warning=True, message=msg)


class ValidationResult(BaseModel):
    """
    Simply a list of diagnostics, in the same order that is shown to the user.
    """

    diagnostics: list[Diagnostic]

    def err(self, msg: str, code: Optional[str] = None):
        self.diagnostics.append(Diagnostic.err(msg, code))

    def warn(self, msg: str, code: Optional[str] = None):
        self.diagnostics.append(Diagnostic.warn(msg, code))
