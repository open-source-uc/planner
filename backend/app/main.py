from .plan.validation.curriculum.tree import CurriculumSpec
from .plan.validation.diagnostic import FlatValidationResult
from .plan.validation.validate import diagnose_plan
from .plan.plan import ValidatablePlan
from .plan.generation import generate_default_plan
from .plan.storage import (
    PlanView,
    LowDetailPlanView,
    store_plan,
    get_user_plans,
    get_plan_details,
    modify_validatable_plan,
    modify_plan_metadata,
    remove_plan,
)
from fastapi import FastAPI, Query, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from .database import prisma
from prisma.models import Course as DbCourse
from .auth import require_authentication, login_cas, UserData
from .sync import run_upstream_sync
from .plan.courseinfo import clear_course_info_cache, course_info
from typing import Optional, Union
from pydantic import BaseModel


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
    try:
        courseinfo = await course_info()
    except Exception:
        # HACK: Previously, JSON was stored incorrectly in the database.
        # This JSON cannot be loaded correctly with the proper way of handling JSON.
        # Therefore, this hack attempts to rebuild courses from scratch if the data is
        # invalid.
        # TODO: Remove this hack once everybody updates the code
        await DbCourse.prisma().delete_many()
        courseinfo = await course_info()
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
    """
    Redirect the browser to this page to initiate authentication.
    """
    return await login_cas(next, ticket)


@app.get("/auth/check")
async def check_auth(user_data: UserData = Depends(require_authentication)):
    """
    Request succeeds if authentication was successful.
    Otherwise, the request fails with 401 Unauthorized.
    """
    return {"message": "Authenticated"}


@app.get("/sync")
# TODO: Require admin permissions for this endpoint.
async def sync_courses():
    """
    Initiate a synchronization of the internal database from external sources.
    """
    await run_upstream_sync()
    return {
        "message": "Course database updated",
    }


class CourseOverview(BaseModel):
    code: str
    name: str
    credits: int


@app.get("/courses/search", response_model=list[CourseOverview])
async def search_courses(text: str):
    """
    Fetches a list of courses that match a given search query string.
    """
    results: list[DbCourse]
    results = await prisma.query_raw(
        """
        SELECT code, name, credits FROM "Course"
        WHERE code LIKE '%' || $1 || '%'
            OR name LIKE '%' || $1 || '%'
        LIMIT 50
        """,
        text,
    )
    return results


@app.get("/courses", response_model=list[DbCourse])
async def get_course_details(codes: list[str] = Query()) -> list[DbCourse]:
    """
    For a list of course codes, fetch a corresponding list of course details.

    Request example: `/api/courses?codes=IIC2233&codes=IIC2173`
    """
    courses: list[DbCourse] = []
    for code in codes:
        course = await DbCourse.prisma().find_unique(where={"code": code})
        if course is None:
            raise HTTPException(status_code=404, detail=f"Course '{code}' not found")
        courses.append(course)
    return courses


@app.post("/plan/rebuild")
async def rebuild_validation_rules():
    """
    Recache course information from internal database.
    """
    clear_course_info_cache()
    info = await course_info()
    return {
        "message": f"Recached {len(info)} courses",
    }


async def debug_get_curriculum() -> CurriculumSpec:
    # TODO: Implement a proper curriculum selector
    return CurriculumSpec(cyear="C2020", major="M170", minor="N776", title="40082")


@app.post("/plan/validate", response_model=FlatValidationResult)
async def validate_plan(plan: ValidatablePlan):
    """
    Validate a plan, generating diagnostics.
    """
    curr = await debug_get_curriculum()
    return (await diagnose_plan(plan, curr)).flatten()


@app.post("/plan/generate")
async def generate_plan(passed: ValidatablePlan):
    """
    Generate a hopefully error-free plan from an initial plan.
    """
    curr = await debug_get_curriculum()
    plan = await generate_default_plan(passed, curr)
    return plan


@app.post("/plan/storage", response_model=PlanView)
async def save_plan(
    name: str,
    plan: ValidatablePlan,
    user_data: UserData = Depends(require_authentication),
) -> PlanView:
    """
    Save a plan with the given name in the storage of the current user.
    Fails if the user is not logged  in.
    """
    return await store_plan(plan_name=name, user_rut=user_data.rut, plan=plan)


@app.get("/plan/storage", response_model=list[LowDetailPlanView])
async def read_plans(
    user_data: UserData = Depends(require_authentication),
) -> list[LowDetailPlanView]:
    """
    Fetches an overview of all the plans in the storage of the current user.
    Fails if the user is not logged in.
    Does not return the courses in each plan, only the plan metadata required
    to show the users their list of plans (e.g. the plan id).
    """
    return await get_user_plans(user_rut=user_data.rut)


@app.get("/plan/storage/details", response_model=PlanView)
async def read_plan(
    plan_id: str, user_data: UserData = Depends(require_authentication)
) -> PlanView:
    """
    Fetch the plan details for a given plan id.
    Requires the current user to be the plan owner.
    """
    return await get_plan_details(user_rut=user_data.rut, plan_id=plan_id)


@app.put("/plan/storage", response_model=PlanView)
async def update_plan(
    plan_id: str,
    new_plan: ValidatablePlan,
    user_data: UserData = Depends(require_authentication),
) -> PlanView:
    """
    Modifies the courses of a plan by id.
    Requires the current user to be the owner of this plan.
    Returns the updated plan.
    """
    return await modify_validatable_plan(
        user_rut=user_data.rut, plan_id=plan_id, new_plan=new_plan
    )


@app.put("/plan/storage/metadata", response_model=PlanView)
async def update_plan_metadata(
    plan_id: str,
    set_name: Union[str, None] = None,
    set_favorite: Union[bool, None] = None,
    user_data: UserData = Depends(require_authentication),
) -> PlanView:
    """
    Modifies the metadata of a plan (currently only `name` or `is_favorite`).
    Modify one attribute per request.
    Requires the current user to be the owner of this plan.
    Returns the updated plan.
    """

    return await modify_plan_metadata(
        user_rut=user_data.rut,
        plan_id=plan_id,
        set_name=set_name,
        set_favorite=set_favorite,
    )


@app.delete("/plan/storage", response_model=PlanView)
async def delete_plan(
    plan_id: str,
    user_data: UserData = Depends(require_authentication),
) -> PlanView:
    """
    Deletes a plan by ID.
    Requires the current user to be the owner of this plan.
    Returns the removed plan.
    """
    return await remove_plan(user_rut=user_data.rut, plan_id=plan_id)
