from asyncio import gather

from prisma.models import Course as DbCourse

from .validate import ValidatablePlan
from ..plan.rules import course_rules
from .logic import Level


# TODO(refactor): repeated function from main.py!
async def get_course_details(code: str):
    return await DbCourse.prisma().find_unique(where={"code": code})


# TODO(refactor): repeated function from main.py!
async def validate_plan(plan: ValidatablePlan):
    rules = await course_rules()
    diag = plan.diagnose(rules)
    return {"valid": len(diag) == 0, "diagnostic": diag}


class CurriculumRecommender:
    """
    Encapsulates all the recommendation logic.
    Scalable and extensible for future curriculum recommendation strategies.
    """

    CREDITS_PER_SEMESTER = 50

    curriculum: list[list[str]] = []

    @classmethod
    async def load_curriculum(cls):
        # by default: 'Malla del major Ingeniería de Software'
        # TODO: load curriculums from an outside API (we hardcode it in the meantime)
        # TODO: implement solution for pseudo-courses
        # (e.g FIS1513/ICE1513. Also 'TEOLOGICO', 'OFG', etc.)
        cls.curriculum = [
            ["MAT1610", "QIM100A", "MAT1203", "ING1004", "FIL2001"],
            ["MAT1620", "FIS1513", "FIS0151", "ICS1513", "IIC1103"],
            ["MAT1630", "FIS1523", "FIS0152", "MAT1640"],
            ["EYP1113", "FIS1533", "FIS0153", "IIC2233"],
            ["IIC2143", "ING2030", "IIC1253"],
            ["IIC2113", "IIC2173", "IIC2413"],
            ["IIC2133", "IIC2513", "IIC2713"],
            ["IIC2154"],
        ]

    @classmethod
    def recommend(cls):
        return ValidatablePlan(classes=cls.curriculum, next_semester=0)


def _compute_courses_to_pass(
    curriculum_classes: list[list[str]], passed_classes: list[list[str]]
):
    flat_curriculum_classes = [
        item for sublist in curriculum_classes for item in sublist
    ]
    return list(
        filter(
            lambda course: all(course not in passed for passed in passed_classes),
            flat_curriculum_classes,
        )
    )


def _make_plan(classes: list[list[str]], passed: ValidatablePlan):
    return ValidatablePlan(
        classes=classes,
        next_semester=passed.next_semester,
        level=Level.PREGRADO,
    )


async def generate_default_plan(passed: ValidatablePlan):
    curriculum = CurriculumRecommender.recommend()

    semesters = passed.classes

    # flat list of all curriculum courses left to pass
    courses_to_pass = _compute_courses_to_pass(curriculum.classes, passed.classes)[::-1]

    # initialize next semester
    semesters.append([])
    while courses_to_pass:
        details = await gather(*(get_course_details(c) for c in semesters[-1]))
        credits = sum(c.credits if c else 0 for c in details)

        next_course = courses_to_pass.pop()

        if credits < CurriculumRecommender.CREDITS_PER_SEMESTER:
            semesters[-1].append(next_course)
        else:
            # TODO: find a more direct way of validating semesters
            validate_semester = await validate_plan(_make_plan(semesters, passed))
            if not validate_semester["valid"]:
                # remove invalid courses from the semester
                invalid = validate_semester["diagnostic"].keys()
                semesters[-1] = list(filter(lambda a: a not in invalid, semesters[-1]))

                # re-insert the removed courses
                courses_to_pass = list(invalid) + courses_to_pass

            # initialize next semester
            semesters.append([next_course])

    return _make_plan(semesters, passed)
