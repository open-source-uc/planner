from .plan.validation.curriculum.tree import Combine, Curriculum
from .plan.validation.diagnostic import ValidationResult
from .plan.validation.validate import diagnose_plan
import pydantic
from .plan.plan import ValidatablePlan
from .plan.generation import generate_default_plan
from fastapi import FastAPI, Query, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from .database import prisma
from prisma.models import Post, Course as DbCourse, CurriculumBlock
from prisma.types import PostCreateInput
from .auth import require_authentication, login_cas, UserData
from .sync import run_upstream_sync
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
    await course_info()
    await recommender.load_curriculum()


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


@app.post("/courses/sync")
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
        curr.blocks.append(pydantic.parse_obj_as(Combine, block.req))
    return curr


@app.post("/plan/validate", response_model=ValidationResult)
async def validate_plan(plan: ValidatablePlan):
    curr = await debug_get_curriculum()
    return await diagnose_plan(plan, curr)


@app.post("/plan/generate")
async def generate_plan(passed: ValidatablePlan):
    curr = await debug_get_curriculum()
    plan = await generate_default_plan(passed, curr)

    return plan
