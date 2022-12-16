from asyncio import gather

from prisma.models import Course as DbCourse

from .validate import ValidatablePlan
from ..plan.rules import course_rules
from .logic import Level


# TODO: repeated function from main.py!
async def get_course_details(code: str):
    return await DbCourse.prisma().find_unique(where={"code": code})


# TODO: repeated function from main.py!
async def validate_plan(plan: ValidatablePlan):
    rules = await course_rules()
    diag = plan.diagnose(rules)
    return {"valid": len(diag) == 0, "diagnostic": diag}


# TODO: move to a CurriculumRecommendator class or something similar
def get_recommended_curriculum():
    # by default: 'Malla del major Ingeniería de Software'
    # TODO: implement solution for pseudo-courses (e.g FIS1513/ICE1513. Also 'TEOLOGICO', 'OFG', etc.)
    # default_curriculum = [
    #     ["MAT1610", "QIM100A", "MAT1203", "ING1004", "FIL2001"],
    #     ["MAT1620", "FIS1513", "FIS0151", "ICS1513", "IIC1103", "TEOLOGICO"],
    #     ["MAT1630", "FIS1523", "FIS0152", "MAT1640", "EXPLORATORIO", "FG-SUSTE"],
    #     ["EYP1113", "FIS1533", "FIS0153", "IIC2233", "OPT-FUND", "FG-HUMAN"],
    #     ["IIC2143", "BIOLOGICO", "ING2030", "IIC1253", "FG-BIEN"],
    #     ["IIC2113", "IIC2173", "IIC2413", "MINOR", "MINOR"],
    #     ["IIC2133", "IIC2513", "IIC2713", "MINOR", "FG-SOCI"],
    #     ["IIC2154", "MINOR", "MINOR", "FG-ARTE", "LIBRE"],
    # ]
    default_curriculum = [
        ["MAT1610", "QIM100A", "MAT1203", "ING1004", "FIL2001"],
        ["MAT1620", "FIS1513", "FIS0151", "ICS1513", "IIC1103"],
        ["MAT1630", "FIS1523", "FIS0152", "MAT1640"],
        ["EYP1113", "FIS1533", "FIS0153", "IIC2233"],
        ["IIC2143", "ING2030", "IIC1253"],
        ["IIC2113", "IIC2173", "IIC2413"],
        ["IIC2133", "IIC2513", "IIC2713"],
        ["IIC2154"],
    ]

    return ValidatablePlan(classes=default_curriculum, next_semester=-1)


# TODO: move to a CurriculumRecommendator class or something similar
CREDITS_PER_SEMESTER = 50


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
    # TODO: remove these comments after discussing the best algorithm
    # ALGORITHM N°1 --> funciona bien pero no es óptimo
    # Es muy rapido pero no valida ni rellena hasta los 50 creditos
    # curriculum = get_recommended_curriculum()
    # semesters = passed.classes
    # courses_to_pass_por_semestre = []
    # for i in range(len(curriculum.classes)):
    #     semestre = []
    #     for j in range(len(curriculum.classes[i])):
    #         curso_esta_aprobado = any(
    #             curriculum.classes[i][j] in sem for sem in passed.classes
    #         )
    #         if not curso_esta_aprobado:
    #             semestre.append(curriculum.classes[i][j])
    #     courses_to_pass_por_semestre.append(semestre)
    # semesters.extend(courses_to_pass_por_semestre)

    # ALGORITHM N°2 --> funciona muy bien pero es lento porque valida cada semestre
    curriculum = get_recommended_curriculum()

    semesters = passed.classes

    # flat list of all curriculum courses left to pass
    courses_to_pass = _compute_courses_to_pass(curriculum.classes, passed.classes)[::-1]

    # initialize next semester
    semesters.append([])
    while courses_to_pass:
        details = await gather(*(get_course_details(c) for c in semesters[-1]))
        credits = sum(c.credits if c else 0 for c in details)

        next_course = courses_to_pass.pop()

        if credits < CREDITS_PER_SEMESTER:
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
