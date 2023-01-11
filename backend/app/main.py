from .plan.validation.curriculum.tree import Block, Curriculum
from .plan.validation.diagnostic import ValidationResult
from .plan.validation.validate import diagnose_plan
import pydantic
from .plan.plan import ValidatablePlan
from .plan.generation import generate_default_plan
from .plan.storage import (
    store_plan,
    get_plans,
    modify_validatable_plan,
    modify_plan_name,
    remove_plan,
)
from fastapi import FastAPI, Query, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from .database import prisma
from prisma.models import Course as DbCourse, CurriculumBlock
from .auth import require_authentication, login_cas, UserData
from .sync import run_upstream_sync
from .plan.courseinfo import clear_course_info_cache, course_info
from .plan.generation import CurriculumRecommender as recommender
from typing import Optional


# Set-up operation IDs for OpenAPI
def custom_generate_unique_id(route: APIRoute):
    if not route.tags:
        return f"{route.name}"
    return f"{route.tags[0]}-{route.name}"


app = FastAPI(generate_unique_id_function=custom_generate_unique_id)

# Allow all CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")  # type: ignore
async def startup():
    await prisma.connect()
    # Prime course info cache
    courseinfo = await course_info()
    await recommender.load_curriculum()
    # Sync courses if database is empty
    if not courseinfo:
        await run_upstream_sync()
        await course_info()


@app.on_event("shutdown")  # type: ignore
async def shutdown():
    await prisma.disconnect()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
async def health():
    # Check database connection
    await prisma.query_raw("SELECT 1")

    return {"message": "OK"}


@app.get("/auth/login")
async def authenticate(next: Optional[str] = None, ticket: Optional[str] = None):
    return await login_cas(next, ticket)


@app.get("/auth/check")
async def check_auth(user_data: UserData = Depends(require_authentication)):
    return {"message": "Authenticated"}


@app.get("/courses/sync")
# TODO: Require admin permissions for this endpoint.
async def sync_courses():
    await run_upstream_sync()
    return {
        "message": "Course database updated",
    }


@app.get("/courses/search")
async def search_courses(text: str):
    results = await prisma.query_raw(
        """
        SELECT code, name FROM "Course"
        WHERE code LIKE '%' || $1 || '%'
            OR name LIKE '%' || $1 || '%'
        LIMIT 50
        """,
        text,
    )
    return results


@app.get("/courses")
async def get_course_details(codes: list[str] = Query()):
    """
    request example: API/courses?codes=IIC2233&codes=IIC2173
    """
    courses: list[DbCourse] = []
    for code in codes:
        course = await DbCourse.prisma().find_unique(where={"code": code})
        if course is None:
            return HTTPException(status_code=404, detail=f"Course '{code}' not found")
        courses.append(course)
    return courses


@app.post("/plan/rebuild")
async def rebuild_validation_rules():
    clear_course_info_cache()
    info = await course_info()
    return {
        "message": f"Recached {len(info)} courses",
    }


async def debug_get_curriculum():
    # TODO: Implement a proper curriculum selector
    blocks = ["plancomun", "formaciongeneral", "major", "minor", "titulo"]
    curr = Curriculum(blocks=[])
    for block_kind in blocks:
        block = await CurriculumBlock.prisma().find_first(where={"kind": block_kind})
        if block is None:
            raise HTTPException(
                status_code=500,
                detail="Database is not initialized"
                + f" (found no block with kind '{block_kind}')",
            )
        curr.blocks.append(pydantic.parse_obj_as(Block, block.req))
    return curr


@app.post("/plan/validate", response_model=ValidationResult)
async def validate_plan(plan: ValidatablePlan):
    curr = await debug_get_curriculum()
    return await diagnose_plan(plan, curr)


@app.post("/plan/generate")
async def generate_plan(passed: ValidatablePlan):
    plan = await generate_default_plan(passed)

    return plan


@app.post("/plan/stored")
async def save_plan(
    name: str,
    plan: ValidatablePlan,
    user_data: UserData = Depends(require_authentication),
):
    stored = await store_plan(plan_name=name, user_rut=user_data.rut, plan=plan)

    return stored


@app.get("/plan/stored")
async def read_plans(user_data: UserData = Depends(require_authentication)):
    plans = await get_plans(user_rut=user_data.rut)

    return plans


@app.put("/plan/stored")
async def update_plan(
    plan_id: str,
    new_plan: ValidatablePlan,
    user_data: UserData = Depends(require_authentication),
):
    updated_plan = await modify_validatable_plan(
        user_rut=user_data.rut, plan_id=plan_id, new_plan=new_plan
    )

    return updated_plan


@app.put("/plan/stored/name")
async def rename_plan(
    plan_id: str,
    new_name: str,
    user_data: UserData = Depends(require_authentication),
):
    updated_plan = await modify_plan_name(
        user_rut=user_data.rut, plan_id=plan_id, new_name=new_name
    )

    return updated_plan


@app.delete("/plan/stored")
async def delete_plan(
    plan_id: str,
    user_data: UserData = Depends(require_authentication),
):
    deleted_plan = await remove_plan(user_rut=user_data.rut, plan_id=plan_id)

    return deleted_plan
