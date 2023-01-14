from datetime import datetime
from fastapi import HTTPException
from prisma import Json
from prisma.models import Plan as DbPlan
from pydantic import BaseModel
import pydantic
from ..plan.plan import ValidatablePlan


class PlanView(BaseModel):
    """
    Detailed, typed view of a plan in the database.
    The only difference between this type and `DbPlan` (ie. the plan schema) is that
    the type of `PlanView.validatable_plan` is `ValidatablePlan`, while the type of
    `Plan.validatable_plan` is `Json`.
    """

    id: str
    created_at: datetime
    updated_at: datetime
    name: str
    user_rut: str
    validatable_plan: ValidatablePlan

    @staticmethod
    def from_db(db: DbPlan) -> "PlanView":
        return PlanView(
            id=db.id,
            created_at=db.created_at,
            updated_at=db.updated_at,
            name=db.name,
            user_rut=db.user_rut,
            validatable_plan=pydantic.parse_raw_as(
                ValidatablePlan, db.validatable_plan
            ),
        )


class LowDetailPlanView(BaseModel):
    """
    Lighter version of the PlanView model.
    This should only contain the required attributes to show the user their plans list
    """

    id: str
    created_at: datetime
    updated_at: datetime
    name: str


async def authorize_plan_access(user_rut: str, plan_id: str) -> DbPlan:
    plan = await DbPlan.prisma().find_unique(where={"id": plan_id})
    if not plan or plan.user_rut != user_rut:
        raise HTTPException(status_code=404, detail="Plan not found in user storage")
    return plan


async def store_plan(plan_name: str, user_rut: str, plan: ValidatablePlan) -> PlanView:
    # TODO: set max 50 plans per user

    stored_plan = await DbPlan.prisma().create(
        data={
            "name": plan_name,
            "user_rut": user_rut,
            "validatable_plan": Json(plan.json()),
        }
    )

    return PlanView.from_db(stored_plan)


async def get_plan_details(user_rut: str, plan_id: str) -> PlanView:
    plan = await authorize_plan_access(user_rut, plan_id)
    return PlanView.from_db(plan)


async def get_user_plans(user_rut: str) -> list[LowDetailPlanView]:
    plans = await DbPlan.prisma().query_raw(
        """
        SELECT id, created_at, updated_at, name, user_rut
        FROM "Plan"
        WHERE user_rut = $1
        """,
        user_rut,
    )

    print(f"returning plans {plans}")

    return plans  # type: ignore


async def modify_validatable_plan(
    user_rut: str, plan_id: str, new_plan: ValidatablePlan
) -> PlanView:
    await authorize_plan_access(user_rut, plan_id)

    updated_plan = await DbPlan.prisma().update(
        where={"id": plan_id}, data={"validatable_plan": Json(new_plan.json())}
    )
    # Must be true because access was authorized
    assert updated_plan is not None

    return PlanView.from_db(updated_plan)


async def modify_plan_metadata(user_rut: str, plan_id: str, new_name: str) -> PlanView:
    await authorize_plan_access(user_rut, plan_id)

    updated_plan = await DbPlan.prisma().update(
        where={
            "id": plan_id,
        },
        data={
            "name": new_name,
        },
    )
    # Must be true because access was authorized
    assert updated_plan is not None

    return PlanView.from_db(updated_plan)


async def remove_plan(user_rut: str, plan_id: str) -> PlanView:
    await authorize_plan_access(user_rut, plan_id)

    deleted_plan = await DbPlan.prisma().delete(where={"id": plan_id})
    # Must be true because access was authorized
    assert deleted_plan is not None

    return PlanView.from_db(deleted_plan)
