from .validation.curriculum.tree import CurriculumSpec
from .plan import ValidatablePlan, Level
from .courseinfo import course_info
from .validation.validate import diagnose_plan_skip_curriculum
from ..sync.siding.translate import fetch_recommended_courses_from_siding


class CurriculumRecommender:
    """
    Encapsulates all the recommendation logic.
    Scalable and extensible for future curriculum recommendation strategies.
    """

    CREDITS_PER_SEMESTER = 50

    @classmethod
    async def recommend(cls, curr: CurriculumSpec) -> ValidatablePlan:
        courses = await fetch_recommended_courses_from_siding(curr)
        return ValidatablePlan(classes=courses, next_semester=0)


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
        school="Ingenieria",
        career="Ingenieria",
    )


async def generate_default_plan(passed: ValidatablePlan, curriculum: CurriculumSpec):
    recommended = await CurriculumRecommender.recommend(curriculum)
    courseinfo = await course_info()

    semesters = passed.classes

    # flat list of all curriculum courses left to pass
    courses_to_pass = _compute_courses_to_pass(recommended.classes, passed.classes)[
        ::-1
    ]

    # initialize next semester
    semesters.append([])
    while courses_to_pass:
        next_course = courses_to_pass.pop()

        credits = sum(
            courseinfo[c].credits if c in courseinfo else 0 for c in semesters[-1]
        )

        if credits < CurriculumRecommender.CREDITS_PER_SEMESTER:
            semesters[-1].append(next_course)
        else:
            # TODO: find a more direct way of validating semesters
            validate_semester = await diagnose_plan_skip_curriculum(
                _make_plan(semesters, passed)
            )
            if len(validate_semester.diagnostics) > 0:
                # remove invalid courses from the semester
                invalid: list[str] = []
                for diag in validate_semester.diagnostics:
                    if diag.course_code is not None:
                        invalid.append(diag.course_code)
                semesters[-1] = list(filter(lambda a: a not in invalid, semesters[-1]))

                # re-insert the removed courses
                courses_to_pass = courses_to_pass + list(invalid)

            # initialize next semester
            semesters.append([next_course])

    return _make_plan(semesters, passed)
