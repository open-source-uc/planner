from abc import abstractmethod
from enum import Enum
from pydantic import BaseModel, Field
from typing import Annotated, Literal, Optional, Union


class Level(Enum):
    """
    An academic level.
    """

    # TODO: Confirm this order, is it correct?
    PREGRADO = 1
    POSTITULO = 2
    MAGISTER = 3
    DOCTORADO = 4


class Class:
    """
    An instance of a course, with a student and semester associated with it.
    """

    code: str
    semester: int

    def __init__(self, code: str, semester: int):
        self.code = code
        self.semester = semester


class LivePlan:
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


class ValidatablePlan(BaseModel):
    classes: list[list[str]]
    next_semester: int
    level: Optional[Level] = None
    school: Optional[str] = None
    program: Optional[str] = None
    career: Optional[str] = None

    def make_live(self, rules: "CourseRules") -> LivePlan:
        return LivePlan(rules, self)

    def validate_classes(self, rules: "CourseRules") -> bool:
        live = self.make_live(rules)
        for sem in range(self.next_semester, len(self.classes)):
            for code in self.classes[sem]:
                if code not in rules.courses:
                    return False
                course = rules.courses[code]
                cl = live.classes[code]
                if not course.requires.validate_class(cl, live):
                    return False
        return True


class BaseExpression(BaseModel):
    """
    A logical expression.
    The requirements that a student must uphold in order to take a course is expressed
    through a combination of expressions.
    """

    @abstractmethod
    def validate_class(self, cl: Class, plan: LivePlan) -> bool:
        pass


class Connector(BaseExpression):
    """
    A logical connector between expressions.
    """

    children: list["Expression"]


class And(Connector):
    """
    Logical AND connector.
    Only satisfied if all of its children are satisfied.
    """

    expr: Literal["and"] = "and"

    def validate_class(self, cl: Class, plan: LivePlan) -> bool:
        ok = True
        for child in self.children:
            ok = ok and child.validate_class(cl, plan)
        return ok


class Or(Connector):
    """
    Logical OR connector.
    Only satisfied if at least one of its children is satisfied.
    """

    expr: Literal["or"] = "or"

    def validate_class(self, cl: Class, plan: LivePlan) -> bool:
        ok = False
        for child in self.children:
            ok = ok or child.validate_class(cl, plan)
        return ok


class MinCredits(BaseExpression):
    """
    A restriction that is only satisfied if the total amount of credits in the previous
    semesters is over a certain threshold.
    """

    expr: Literal["creds"] = "creds"

    min_credits: int

    def validate_class(self, cl: Class, plan: LivePlan) -> bool:
        # approved_credits[sem] contains the total amount of credits approved in
        # semesters [0, sem)
        return plan.approved_credits[cl.semester] >= self.min_credits


class ReqLevel(BaseExpression):
    """
    Express that this course requires a certain academic level.
    """

    expr: Literal["lvl"] = "lvl"

    min_level: Level

    def validate_class(self, cl: Class, plan: LivePlan) -> bool:
        if plan.plan.level is None:
            # TODO: Does everybody have a level?
            # Should planner reject guests with courses that have level restrictions?
            return False
        # TODO: Is this a `>=` relationship or actually an `=` relationship?
        return plan.plan.level.value >= self.min_level


class ReqSchool(BaseExpression):
    """
    Express that this course requires the student to belong to a particular school.
    """

    expr: Literal["school"] = "school"

    school: str

    def validate_class(self, cl: Class, plan: LivePlan) -> bool:
        return plan.plan.school == self.school


class ReqNotSchool(BaseExpression):
    """
    Express that this course requires the student to NOT belong to a particular school.
    """

    expr: Literal["!school"] = "!school"

    school: str

    def validate_class(self, cl: Class, plan: LivePlan) -> bool:
        return plan.plan.school != self.school


class ReqProgram(BaseExpression):
    """
    Express that this course requires the student to belong to a particular program.
    """

    expr: Literal["program"] = "program"

    program: str

    def validate_class(self, cl: Class, plan: LivePlan) -> bool:
        return plan.plan.program == self.program


class ReqNotProgram(BaseExpression):
    """
    Express that this course requires the student to NOT belong to a particular program.
    """

    expr: Literal["!program"] = "!program"

    program: str

    def validate_class(self, cl: Class, plan: LivePlan) -> bool:
        return plan.plan.program != self.program


class ReqCareer(BaseExpression):
    """
    Express that this course requires the student to belong to a particular career.
    """

    expr: Literal["career"] = "career"

    career: str

    def validate_class(self, cl: Class, plan: LivePlan) -> bool:
        return plan.plan.career == self.career


class ReqNotCareer(BaseExpression):
    """
    Express that this course requires the student to NOT belong to a particular career.
    """

    expr: Literal["!career"] = "!career"

    career: str

    def validate_class(self, cl: Class, plan: LivePlan) -> bool:
        return plan.plan.career != self.career


class CourseRequirement(BaseExpression):
    """
    Require the student to have taken a course in the previous semesters.
    """

    expr: Literal["req"] = "req"

    code: str

    def validate_class(self, cl: Class, plan: LivePlan) -> bool:
        if self.code not in plan.classes:
            return False
        req_cl = plan.classes[self.code]
        return req_cl.semester < cl.semester


class CourseCorequirement(BaseExpression):
    """
    Require the student to have taken or be taking a course in the previous semesters
    (including the current semester).
    """

    expr: Literal["coreq"] = "coreq"

    code: str

    def validate_class(self, cl: Class, plan: LivePlan) -> bool:
        if self.code not in plan.classes:
            return False
        req_cl = plan.classes[self.code]
        return req_cl.semester <= cl.semester


Expression = Annotated[
    Union[
        And,
        Or,
        MinCredits,
        ReqLevel,
        ReqSchool,
        ReqNotSchool,
        ReqProgram,
        ReqNotProgram,
        ReqCareer,
        ReqNotCareer,
        CourseRequirement,
        CourseCorequirement,
    ],
    Field(discriminator="expr"),
]
And.update_forward_refs()
Or.update_forward_refs()
MinCredits.update_forward_refs()
ReqLevel.update_forward_refs()
ReqSchool.update_forward_refs()
ReqNotSchool.update_forward_refs()
ReqProgram.update_forward_refs()
ReqNotProgram.update_forward_refs()
ReqCareer.update_forward_refs()
ReqNotCareer.update_forward_refs()
CourseRequirement.update_forward_refs()
CourseCorequirement.update_forward_refs()


class Course(BaseModel):
    """
    A single course, with an associated code.
    This course is not "instantiated", it is an abstract course prototype.
    """

    code: str
    credits: int
    requires: Expression


class CourseRules(BaseModel):
    """
    A collection of courses with their own requirements.
    """

    courses: dict[str, Course]
