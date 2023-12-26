from functools import cache
from typing import Annotated, Literal

import pydantic
from pydantic import BaseModel, Field

from app.plan.course import ConcreteId, EquivalenceId, PseudoCourse
from app.plan.courseinfo import course_info
from app.plan.plan import ValidatablePlan
from app.plan.validation.curriculum.solve import solve_curriculum
from app.plan.validation.curriculum.tree import (
    CurriculumSpec,
)
from app.sync import get_curriculum


class PlanV1(BaseModel):
    version: Literal["0.0.1"]
    classes: list[list[PseudoCourse]]
    level: str | None
    school: str | None
    program: str | None
    career: str | None
    curriculum: CurriculumSpec


StorablePlan = Annotated[
    PlanV1 | ValidatablePlan,
    Field(discriminator="version"),
]


@cache
def _load_v0_0_1_legacy_map() -> dict[str, str]:
    return pydantic.parse_file_as(
        dict[str, str],
        "../static-curriculum-data/legacy-mock-map-1.json",
    )


async def _migrate_v0_0_1(plan: PlanV1) -> ValidatablePlan:
    """
    Migrate a 0.0.1 plan to the next version (0.0.2).

    This requires mapping equivalence codes.
    This also requires solving the plan in order to assign blocks.
    """

    equivmap = _load_v0_0_1_legacy_map()

    # Auxiliary function to map equivalence codes
    def map_code(code: str) -> str:
        if code in equivmap:
            return equivmap[code]
        if code.startswith("!"):
            return f"MAJOR-LIST-{code[1:]}"
        if code.startswith("?"):
            return f"MAJOR-EQUIV-{code[1:]}"
        return code

    # Auxiliary function to map equivalences
    def map_equiv(equiv: EquivalenceId) -> EquivalenceId:
        return EquivalenceId(code=map_code(equiv.code), credits=equiv.credits)

    # Create the modern plan
    newplan = ValidatablePlan(
        version="0.0.2",
        classes=[
            [
                ConcreteId(
                    code=c.code,
                    equivalence=map_equiv(c.equivalence) if c.equivalence else None,
                    failed=c.failed,
                )
                if isinstance(c, ConcreteId)
                else map_equiv(c)
                for c in sem
            ]
            for sem in plan.classes
        ],
        level=plan.level,
        school=plan.school,
        program=plan.program,
        career=plan.career,
        curriculum=plan.curriculum,
    )

    # Solve the plan in order to assign blocks to courses
    g = solve_curriculum(
        await course_info(),
        newplan.curriculum,
        await get_curriculum(plan.curriculum),
        newplan.classes,
    )
    g.execute_recolors(newplan.classes)

    return newplan


async def migrate_plan(storable: StorablePlan) -> ValidatablePlan:
    """
    Convert a `StorablePlan` (which is a superset of `ValidatablePlan`) into a
    `ValidatablePlan`.
    For most cases this is a no-op, but if the storable plan is not the latest version,
    it must perform a migration.
    """
    if isinstance(storable, PlanV1):
        storable = await _migrate_v0_0_1(storable)
    return storable
