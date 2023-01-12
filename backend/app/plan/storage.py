from fastapi import HTTPException
from prisma import Json
from prisma.models import Plan
from ..plan.plan import ValidatablePlan


async def authorize_plan_access(user_rut: str, plan_id: str):
    user_plans = await Plan.prisma().find_many(where={"user_rut": user_rut})
    if plan_id not in [p.id for p in user_plans]:
        raise HTTPException(status_code=404, detail="Plan not found in user storage")


async def store_plan(plan_name: str, user_rut: str, plan: ValidatablePlan):
    # TODO: set max 50 plans per user

    stored_plan = await Plan.prisma().create(
        data={
            "name": plan_name,
            "user_rut": user_rut,
            "validatable_plan": Json(plan.dict()),
        }
    )

    return stored_plan


async def get_plan_details(user_rut: str, plan_id: str):
    await authorize_plan_access(user_rut, plan_id)

    plan = await Plan.prisma().find_unique(where={"id": plan_id})

    return plan


async def get_user_plans(user_rut: str):
    plans = await Plan.prisma().find_many(where={"user_rut": user_rut})

    return plans


async def modify_validatable_plan(
    user_rut: str, plan_id: str, new_plan: ValidatablePlan
):
    await authorize_plan_access(user_rut, plan_id)

    updated_plan = await Plan.prisma().update(
        where={"id": plan_id}, data={"validatable_plan": Json(new_plan.dict())}
    )

    return updated_plan


async def modify_plan_metadata(user_rut: str, plan_id: str, new_name: str):
    await authorize_plan_access(user_rut, plan_id)

    updated_plan = await Plan.prisma().update(
        where={
            "id": plan_id,
        },
        data={
            "name": new_name,
        },
    )

    return updated_plan


async def remove_plan(user_rut: str, plan_id: str):
    await authorize_plan_access(user_rut, plan_id)

    deleted_plan = await Plan.prisma().delete(where={"id": plan_id})

    return deleted_plan
