from .plan.validation.curriculum.solve import solve_curriculum
from .user.info import StudentContext
from .plan.validation.diagnostic import FlatValidationResult
from .plan.validation.validate import diagnose_plan
from .plan.plan import ValidatablePlan
from .plan.generation import generate_empty_plan, generate_recommended_plan
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
from prisma.models import (
    Course as DbCourse,
    Equivalence as DbEquivalence,
    Major as DbMajor,
    Minor as DbMinor,
    Title as DbTitle,
)
from prisma.types import CourseWhereInput, CourseWhereInputRecursive2
from .user.auth import require_authentication, login_cas, UserKey
from . import sync
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
    if len(courseinfo.courses) == 0:
        await sync.run_upstream_sync()
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
async def check_auth(user_data: UserKey = Depends(require_authentication)):
    """
    Request succeeds if authentication was successful.
    Otherwise, the request fails with 401 Unauthorized.
    """
    return {"message": "Authenticated"}


@app.get("/student/info", response_model=StudentContext)
async def get_student_info(user: UserKey = Depends(require_authentication)):
    """
    Get the student info for the currently logged in user.
    Requires authentication (!)
    This forwards a request to the SIDING service.
    """
    return await sync.get_student_data(user)


# TODO: This HTTP method should not be GET, as it has side-effects.
# For the meantime this makes it easier to trigger syncs, but in the future this must
# change.
@app.get("/sync")
# TODO: Require admin permissions for this endpoint.
async def sync_courses():
    """
    Initiate a synchronization of the internal database from external sources.
    """
    await sync.run_upstream_sync()
    return {
        "message": "Course database updated",
    }


class CourseOverview(BaseModel):
    code: str
    name: str
    credits: int
    school: str


def _get_course_filter(
    name: Optional[str] = None,
    credits: Optional[int] = None,
    school: Optional[str] = None,
    code_whitelist: Optional[list[str]] = None,
):
    filter = CourseWhereInput()
    if name is not None:
        name_parts: list[CourseWhereInputRecursive2] = list(
            map(
                lambda name_part: {
                    "name": {"contains": name_part, "mode": "insensitive"}
                },
                name.split(),
            )
        )
        filter["OR"] = [
            {"code": {"contains": name, "mode": "insensitive"}},
            {"AND": name_parts},
        ]
    if credits is not None:
        filter["credits"] = credits
    if school is not None:
        filter["school"] = {"contains": school, "mode": "insensitive"}
    if code_whitelist is not None:
        filter["code"] = {
            "in": code_whitelist,
        }
    return filter


@app.get("/courses/search", response_model=list[CourseOverview])
async def search_courses(
    name: Optional[str] = None,
    credits: Optional[int] = None,
    school: Optional[str] = None,
):
    """
    Fetches a list of courses that match the given name (or code),
    credits and school.
    """
    filter = _get_course_filter(name=name, credits=credits, school=school)
    return await DbCourse.prisma().find_many(where=filter, take=50)


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


async def _filter_courses(
    courses: list[str],
    name: Optional[str] = None,
    credits: Optional[int] = None,
    school: Optional[str] = None,
) -> list[str]:
    filter = _get_course_filter(
        name=name, credits=credits, school=school, code_whitelist=courses
    )
    filtered: list[DbCourse] = await DbCourse.prisma().find_many(where=filter, take=50)
    return list(map(lambda c: c.code, filtered))


@app.get("/equivalences", response_model=list[DbEquivalence])
async def get_equivalence_details(
    codes: list[str] = Query(),
    filter_name: Optional[str] = None,
    filter_credits: Optional[int] = None,
    filter_school: Optional[str] = None,
) -> list[DbEquivalence]:
    """
    For a list of equivalence codes, fetch a corresponding list of equivalence details
    with the `courses` attribute filtered.
    """
    equivs: list[DbEquivalence] = []
    for code in codes:
        equiv = await DbEquivalence.prisma().find_unique(where={"code": code})
        if equiv is None:
            raise HTTPException(
                status_code=404, detail=f"Equivalence '{code}' not found"
            )
        equiv.courses = await _filter_courses(
            courses=equiv.courses,
            name=filter_name,
            credits=filter_credits,
            school=filter_school,
        )
        equivs.append(equiv)
    return equivs


@app.post("/plan/rebuild")
async def rebuild_validation_rules():
    """
    Recache course information from internal database.
    """
    clear_course_info_cache()
    info = await course_info()
    return {
        "message": f"Recached {len(info.courses)} courses and "
        f"{len(info.equivs)} equivalences",
    }


@app.get("/plan/empty_for", response_model=ValidatablePlan)
async def empty_plan_for_user(user_data: UserKey = Depends(require_authentication)):
    """
    Generate an empty plan using the current user as context.
    For example, the created plan includes all passed courses, uses the curriculum
    version for the given user and selects the student's official choice of
    major/minor/title if available.

    (Currently this is equivalent to `empty_guest_plan()` until we get user data)
    """
    return await generate_empty_plan(user_data)


@app.get("/plan/empty_guest", response_model=ValidatablePlan)
async def empty_guest_plan():
    """
    Generates a generic empty plan with no user context, using the latest curriculum
    version.
    """
    return await generate_empty_plan(None)


@app.post("/plan/validate", response_model=FlatValidationResult)
async def validate_guest_plan(plan: ValidatablePlan):
    """
    Validate a plan, generating diagnostics.
    """
    return (await diagnose_plan(plan, user_ctx=None)).flatten()


@app.post("/plan/validate_for", response_model=FlatValidationResult)
async def validate_plan_for_user(
    plan: ValidatablePlan, user: UserKey = Depends(require_authentication)
):
    """
    Validate a plan, generating diagnostics.
    Includes warnings tailored for the given user.
    """
    user_ctx = await sync.get_student_data(user)
    return (await diagnose_plan(plan, user_ctx)).flatten()


@app.post("/plan/curriculum_graph")
async def get_curriculum_validation_graph(plan: ValidatablePlan) -> str:
    """
    Get the curriculum validation graph for a certain plan, in Graphviz DOT format.
    Useful for debugging and kind of a bonus easter egg.
    """
    courseinfo = await course_info()
    curriculum = await sync.get_curriculum(plan.curriculum)
    g = solve_curriculum(courseinfo, curriculum, plan.classes)
    return g.dump_graphviz(plan.classes)


@app.post("/plan/generate", response_model=ValidatablePlan)
async def generate_plan(passed: ValidatablePlan):
    """
    From a base plan, generate a new plan that should lead the user to earn their title
    of choice.
    """
    plan = await generate_recommended_plan(passed)
    return plan


@app.post("/plan/storage", response_model=PlanView)
async def save_plan(
    name: str,
    plan: ValidatablePlan,
    user: UserKey = Depends(require_authentication),
) -> PlanView:
    """
    Save a plan with the given name in the storage of the current user.
    Fails if the user is not logged  in.
    """
    return await store_plan(plan_name=name, user=user, plan=plan)


@app.get("/plan/storage", response_model=list[LowDetailPlanView])
async def read_plans(
    user: UserKey = Depends(require_authentication),
) -> list[LowDetailPlanView]:
    """
    Fetches an overview of all the plans in the storage of the current user.
    Fails if the user is not logged in.
    Does not return the courses in each plan, only the plan metadata required
    to show the users their list of plans (e.g. the plan id).
    """
    return await get_user_plans(user)


@app.get("/plan/storage/details", response_model=PlanView)
async def read_plan(
    plan_id: str, user: UserKey = Depends(require_authentication)
) -> PlanView:
    """
    Fetch the plan details for a given plan id.
    Requires the current user to be the plan owner.
    """
    return await get_plan_details(user=user, plan_id=plan_id)


@app.put("/plan/storage", response_model=PlanView)
async def update_plan(
    plan_id: str,
    new_plan: ValidatablePlan,
    user: UserKey = Depends(require_authentication),
) -> PlanView:
    """
    Modifies the courses of a plan by id.
    Requires the current user to be the owner of this plan.
    Returns the updated plan.
    """
    return await modify_validatable_plan(user=user, plan_id=plan_id, new_plan=new_plan)


@app.put("/plan/storage/metadata", response_model=PlanView)
async def update_plan_metadata(
    plan_id: str,
    set_name: Union[str, None] = None,
    set_favorite: Union[bool, None] = None,
    user: UserKey = Depends(require_authentication),
) -> PlanView:
    """
    Modifies the metadata of a plan (currently only `name` or `is_favorite`).
    Modify one attribute per request.
    Requires the current user to be the owner of this plan.
    Returns the updated plan.
    """

    return await modify_plan_metadata(
        user=user,
        plan_id=plan_id,
        set_name=set_name,
        set_favorite=set_favorite,
    )


@app.delete("/plan/storage", response_model=PlanView)
async def delete_plan(
    plan_id: str,
    user: UserKey = Depends(require_authentication),
) -> PlanView:
    """
    Deletes a plan by ID.
    Requires the current user to be the owner of this plan.
    Returns the removed plan.
    """
    return await remove_plan(user=user, plan_id=plan_id)


@app.get("/offer/major", response_model=list[DbMajor])
async def get_majors(cyear: str):
    """
    Get all the available majors for a given curriculum version (cyear).
    """
    return await DbMajor.prisma().find_many(
        where={
            "cyear": cyear,
        }
    )


@app.get("/offer/minor", response_model=list[DbMinor])
async def get_minors(cyear: str, major_code: Optional[str] = None):
    if major_code is None:
        return await DbMinor.prisma().find_many(
            where={
                "cyear": cyear,
            }
        )
    else:
        return await DbMinor.prisma().query_raw(
            """
            SELECT *
            FROM "Minor", "MajorMinor"
            WHERE "MajorMinor".minor = "Minor".code
                AND "MajorMinor".major = $2
                AND "MajorMinor".cyear = $1
                AND "Minor".cyear = $1
            """,
            cyear,
            major_code,
        )


@app.get("/offer/title", response_model=list[DbTitle])
async def get_titles(cyear: str):
    return await DbTitle.prisma().find_many(
        where={
            "cyear": cyear,
        }
    )
