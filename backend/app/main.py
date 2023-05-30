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
from .sync.siding import translate as siding_translate
from fastapi import FastAPI, Query, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from .database import prisma
from prisma.models import (
    AccessLevel as DbAccessLevel,
    Course as DbCourse,
    Major as DbMajor,
    Minor as DbMinor,
    Title as DbTitle,
)
from prisma.types import CourseWhereInput, CourseWhereInputRecursive2
from .user.auth import (
    require_authentication,
    require_mod_auth,
    require_admin_auth,
    login_cas,
    UserKey,
    ModKey,
    AdminKey,
    AccessLevelOverview,
)
from . import sync
from .plan.courseinfo import (
    CourseDetails,
    EquivDetails,
    clear_course_info_cache,
    course_info,
    make_searchable_name,
)
from .sync.siding.client import client as siding_soap_client
from typing import Optional, Union
from pydantic import BaseModel
from unidecode import unidecode


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
    # Setup SIDING webservice
    siding_soap_client.on_startup()
    # Prime course info cache
    courseinfo = await course_info()
    # Sync courses if database is empty
    if len(courseinfo.courses) == 0:
        await sync.run_upstream_sync()
        await course_info()


@app.on_event("shutdown")  # type: ignore
async def shutdown():
    await prisma.disconnect()
    siding_soap_client.on_shutdown()


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
    Request succeeds if user authentication was successful.
    Otherwise, the request fails with 401 Unauthorized.
    """
    return {"message": "Authenticated"}


@app.get("/auth/check/mod")
async def check_mod(user_data: ModKey = Depends(require_mod_auth)):
    """
    Request succeeds if user authentication and mod authorization were successful.
    Otherwise, the request fails with 401 Unauthorized or 403 Forbidden.
    """
    return {"message": "Authenticated with mod access"}


@app.get("/auth/check/admin")
async def check_admin(user_data: AdminKey = Depends(require_admin_auth)):
    """
    Request succeeds if user authentication and admin authorization were successful.
    Otherwise, the request fails with 401 Unauthorized or 403 Forbidden.
    """
    return {"message": "Authenticated with admin access"}


@app.get("/auth/mod", response_model=list[AccessLevelOverview])
async def view_mods(user_data: AdminKey = Depends(require_admin_auth)):
    """
    Show a list of all current mods with username and RUT. Up to 50 records.
    """
    mods = await DbAccessLevel.prisma().find_many(take=50)

    named_mods: list[AccessLevelOverview] = []
    for mod in mods:
        named_mods.append(AccessLevelOverview(**dict(mod)))
        try:
            print(f"fetching user data for user {mod.user_rut} from SIDING...")
            # TODO: check if this function works for non-students
            data = await siding_translate.fetch_student_info(mod.user_rut)
            named_mods[-1].name = data.full_name
        finally:
            # Ignore if couldn't get the name by any reason to at least show
            # the RUT, which is more important.
            pass
    return named_mods


@app.post("/auth/mod")
async def add_mod(rut: str, user_data: AdminKey = Depends(require_admin_auth)):
    """
    Give mod access to a user with the specified RUT.
    """
    return await DbAccessLevel.prisma().upsert(
        where={
            "user_rut": rut,
        },
        data={
            "create": {
                "user_rut": rut,
                "is_mod": True,
            },
            "update": {
                "is_mod": True,
            },
        },
    )


@app.delete("/auth/mod")
async def remove_mod(rut: str, user_data: AdminKey = Depends(require_admin_auth)):
    """
    Remove mod access from a user with the specified RUT.

    TODO: add JWT tracking system for mods to be able to instantly revoke unexpired
    token access after permission removal.
    """
    mod_record = await DbAccessLevel.prisma().find_unique(where={"user_rut": rut})

    if not mod_record:
        raise HTTPException(status_code=404, detail="Mod not found")
    return await DbAccessLevel.prisma().delete(where={"user_rut": rut})


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
async def sync_database(
    courses: bool = False,
    offer: bool = False,
    admin_key: AdminKey = Depends(require_admin_auth),
):
    """
    Initiate a synchronization of the internal database from external sources.
    """
    await sync.run_upstream_sync(courses, offer)
    return {
        "message": "Database updated from external sources",
    }


class CourseOverview(BaseModel):
    code: str
    name: str
    credits: int
    school: str
    area: Optional[str]
    is_available: bool


class CourseFilter(BaseModel):
    # Only allow courses that match the given search string, in name or course code.
    text: Optional[str] = None
    # Only allow courses that have the given amount of credits.
    credits: Optional[int] = None
    # Only allow courses matching the given school.
    school: Optional[str] = None
    # Only allow courses that match the given availability.
    available: Optional[bool] = None
    # Only allow courses available on the given semester.
    on_semester: Optional[tuple[bool, bool]] = None
    # Only allow courses that are members of the given equivalence.
    equiv: Optional[str] = None

    def as_db_filter(self) -> CourseWhereInput:
        filter = CourseWhereInput()
        if self.text is not None:
            search_text = make_searchable_name(self.text)
            name_parts: list[CourseWhereInputRecursive2] = list(
                map(
                    lambda text_part: {"searchable_name": {"contains": text_part}},
                    search_text.split(),
                )
            )
            filter["OR"] = [
                {"code": {"contains": search_text.upper()}},
                {"AND": name_parts},
            ]
        if self.credits is not None:
            filter["credits"] = self.credits
        if self.school is not None:
            ascii_school = unidecode(self.school)
            filter["school"] = {"contains": ascii_school, "mode": "insensitive"}
        if self.available is not None:
            filter["is_available"] = self.available
        if self.on_semester is not None:
            filter["semestrality_first"] = self.on_semester[0]
            filter["semestrality_second"] = self.on_semester[1]
        if self.equiv is not None:
            filter["equivs"] = {"some": {"equiv_code": self.equiv}}
        return filter


# This should be a GET request, but FastAPI does not support JSON in GET requests
# easily.
# See https://github.com/tiangolo/fastapi/discussions/7919
@app.post("/courses/search/details", response_model=list[CourseOverview])
async def search_course_details(filter: CourseFilter):
    """
    Fetches a list of courses that match the given name (or code),
    credits and school.
    """
    return await DbCourse.prisma().find_many(where=filter.as_db_filter(), take=50)


# This should be a GET request, but FastAPI does not support JSON in GET requests
# easily.
# See https://github.com/tiangolo/fastapi/discussions/7919
@app.post("/courses/search/codes", response_model=list[str])
async def search_course_codes(filter: CourseFilter):
    """
    Fetches a list of courses that match the given name (or code),
    credits and school.
    Returns only the course codes, but allows up to 3000 results.
    """
    codes = list(
        map(
            lambda c: c.code,
            await DbCourse.prisma().find_many(where=filter.as_db_filter(), take=3000),
        )
    )
    return codes


@app.get("/courses", response_model=list[CourseDetails])
async def get_course_details(codes: list[str] = Query()) -> list[CourseDetails]:
    """
    For a list of course codes, fetch a corresponding list of course details.

    Request example: `/api/courses?codes=IIC2233&codes=IIC2173`
    """

    courseinfo = await course_info()
    courses: list[CourseDetails] = []
    for code in codes:
        course = courseinfo.try_course(code)
        if course is None:
            raise HTTPException(status_code=404, detail=f"Course '{code}' not found")
        courses.append(course)
    return courses


@app.get("/equivalences", response_model=list[EquivDetails])
async def get_equivalence_details(
    codes: list[str] = Query(),
) -> list[EquivDetails]:
    """
    For a list of equivalence codes, fetch the raw equivalence details, without any
    filtering.
    To filter courses for a specific equivalence, use `search_courses` with an
    equivalence filter.
    """

    courseinfo = await course_info()
    equivs: list[EquivDetails] = []
    for code in codes:
        equiv = courseinfo.try_equiv(code)
        if equiv is None:
            raise HTTPException(
                status_code=404, detail=f"Equivalence '{code}' not found"
            )
        equivs.append(equiv)
    return equivs


@app.post("/plan/rebuild")
async def rebuild_validation_rules():
    """
    Recache course information from internal database.
    """
    await clear_course_info_cache()
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
    return (await diagnose_plan(plan, user_ctx=None)).flatten(plan)


@app.post("/plan/validate_for", response_model=FlatValidationResult)
async def validate_plan_for_user(
    plan: ValidatablePlan, user: UserKey = Depends(require_authentication)
):
    """
    Validate a plan, generating diagnostics.
    Includes warnings tailored for the given user.
    """
    user_ctx = await sync.get_student_data(user)
    return (await diagnose_plan(plan, user_ctx)).flatten(plan)


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
