from .plan.validation.curriculum.tree import Curriculum
from .plan.validation.diagnostic import ValidationResult
from .plan.validation.validate import diagnose_plan
from .plan.plan import ValidatablePlan
from .plan.generation import generate_default_plan
from fastapi import FastAPI, Query, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from .database import prisma
from prisma.models import Post, Course as DbCourse
from prisma.types import PostCreateInput
from .auth import require_authentication, login_cas, UserData
from .sync import run_upstream_sync
from .sync.siding.translate import fetch_curriculum_from_siding
from .plan.courseinfo import clear_course_info_cache, course_info
from .plan.generation import CurriculumRecommender as recommender
from typing import List, Optional


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


@app.get("/posts")
async def get_posts() -> List[Post]:
    return await Post.prisma().find_many()


@app.put("/posts")
async def create_post(post: PostCreateInput):
    return await prisma.post.create(post)


@app.get("/auth/login")
async def authenticate(next: Optional[str] = None, ticket: Optional[str] = None):
    return await login_cas(next, ticket)


@app.get("/auth/check")
async def check_auth(user_data: UserData = Depends(require_authentication)):
    return {"message": "Authenticated"}


@app.get("/sync")
# TODO: Require admin permissions for this endpoint.
async def sync_courses():
    await run_upstream_sync()
    return {
        "message": "Course database updated",
    }


@app.get("/courses/search")
async def search_courses(text: str):
    results: list[DbCourse]
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


async def debug_get_curriculum() -> Curriculum:
    # TODO: Implement a proper curriculum selector
    return await fetch_curriculum_from_siding("C2020", "M170", "N776", "40082")


@app.post("/plan/validate", response_model=ValidationResult)
async def validate_plan(plan: ValidatablePlan):
    curr = await debug_get_curriculum()
    return await diagnose_plan(plan, curr)


@app.post("/plan/generate")
async def generate_plan(passed: ValidatablePlan):
    plan = await generate_default_plan(passed)

    return plan


# TODO: Remove before merging
# DEBUG
@app.get("/test_siding")
async def test_siding():
    from .sync.siding import translate

    await translate.test_translate()
