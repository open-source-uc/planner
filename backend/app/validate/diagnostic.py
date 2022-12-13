from .logic import Operator, Const
from .models import CourseRules, Expr, Level, ReqCareer, ReqProgram, ReqSchool
from enum import Enum
from pydantic import BaseModel
from typing import Optional


class Class:
    """
    An instance of a course, with a student and semester associated with it.
    """

    code: str
    semester: int

    def __init__(self, code: str, semester: int):
        self.code = code
        self.semester = semester


class PlanContext:
    rules: "CourseRules"
    # A dictionary of classes and their respective semesters
    classes: dict[str, Class]
    # A list of accumulated total approved credits per semester
    # approved_credits[i] contains the amount of approved credits in the range [0, i)
    approved_credits: list[int]
    # Original validatable plan object.
    plan: "ValidatablePlan"

    def __init__(self, rules: "CourseRules", plan: "ValidatablePlan"):
        # Map from coursecode to class
        classes = {}
        # List of total approved credits per semester
        acc_credits = [0]
        # Iterate over semesters
        for sem in range(len(plan.classes)):
            creds = acc_credits[-1]
            # Iterate over classes in this semester
            for code in plan.classes[sem]:
                # Add this class to the map
                if code not in classes:
                    classes[code] = Class(code, sem)
                # Accumulate credits
                # TODO: Do repeated courses count towards this credit count?
                if code in rules.courses:
                    creds += rules.courses[code].credits
            acc_credits.append(creds)
        self.rules = rules
        self.classes = classes
        self.approved_credits = acc_credits
        self.plan = plan

    def validate(self) -> dict[str, str]:
        diags: dict[str, str] = {}
        for sem in range(self.plan.next_semester, len(self.plan.classes)):
            for code in self.plan.classes[sem]:
                if code not in self.rules.courses:
                    diags[code] = "Curso desconocido"
                    continue
                course = self.rules.courses[code]
                cl = self.classes[code]
                diag = self.diagnose(cl, course.requires)
                if diag is not None:
                    diags[code] = diag
        return diags

    def is_satisfied(self, cl: Class, expr: "Expr") -> bool:
        """
        Check if the this plan satisfies the given logical expression, with the given
        class as context.
        """
        if isinstance(expr, Operator):
            val = expr.neutral
            for child in expr.children:
                val = expr.op(val, self.is_satisfied(cl, child))
            return val
        if isinstance(expr, Const):
            return expr.value
        return expr.is_satisfied(self, cl)

    def diagnose(self, cl: Class, expr: "Expr") -> Optional[str]:
        if self.is_satisfied(cl, expr):
            return None
        # Some requirement is not satisfied
        # Fill in satisfied requirements, and then simplify resulting expression to get
        # an indication of "what do I have to do in order to satisfy requirements"
        simplified = self.strip_satisfied(cl, expr).simplify()
        if isinstance(simplified, Const):
            simplified = self.strip_satisfied(cl, expr, fix_career=False).simplify()
        # Show this expression
        return f"Requisitos faltantes: {simplified}"

    def strip_satisfied(self, cl: Class, expr: Expr, fix_career: bool = True) -> Expr:
        if isinstance(expr, Operator):
            changed = False
            new_children: list[Expr] = []
            for child in expr.children:
                new_child = self.strip_satisfied(cl, child)
                new_children.append(new_child)
                if new_child is not child:
                    changed = True
            if changed:
                return Operator.create(expr.neutral, tuple(new_children))
            else:
                return expr
        if isinstance(expr, Const):
            return expr
        if fix_career and isinstance(expr, (ReqProgram, ReqCareer, ReqSchool)):
            return Const(value=expr.is_satisfied(self, cl))
        if expr.is_satisfied(self, cl):
            return Const(value=True)
        else:
            return expr


class Severity(Enum):
    NONE = 0
    FIXABLE = 1
    FATAL = 2


class ValidatablePlan(BaseModel):
    classes: list[list[str]]
    next_semester: int
    level: Optional[Level] = None
    school: Optional[str] = None
    program: Optional[str] = None
    career: Optional[str] = None

    def make_live(self, rules: "CourseRules") -> PlanContext:
        return PlanContext(rules, self)
