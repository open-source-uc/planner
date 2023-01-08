from .plan.validation.curriculum.tree import Combine, Curriculum
from .plan.validation.diagnostic import ValidationResult
from .plan.validation.validate import diagnose_plan
import pydantic
from .plan.plan import ValidatablePlan, Level
from .plan.generation import generate_default_plan
from fastapi import FastAPI, Query, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from .database import prisma
from prisma.models import Post, Course as DbCourse, CurriculumBlock
from prisma.types import (
    PostCreateInput,
    PlanCreateInput,
    PlanSemesterCreateInput,
    PlanClassCreateInput,
)
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
    plan = await generate_default_plan(passed)

    return plan


@app.post("/plan/stored")
async def save_plan(
    name: str,
    plan: ValidatablePlan,
    user_data: UserData = Depends(require_authentication),
):
    # TODO: move logic to external method
    # TODO: set max 50 plans per user

    stored_plan = await prisma.plan.create(
        PlanCreateInput(
            name=name,
            user_rut=user_data.rut,
            next_semester=plan.next_semester,
            level=plan.level,
            school=plan.school,
            program=plan.program,
            career=plan.career,
        )
    )

    for i, sem in enumerate(plan.classes):
        stored_semester = await prisma.plansemester.create(
            PlanSemesterCreateInput(plan_id=stored_plan.id, number=i + 1)
        )
        for cls in sem:
            await prisma.planclass.create(
                PlanClassCreateInput(semester_id=stored_semester.id, class_code=cls)
            )

    return stored_plan


@app.get("/plan/stored")
async def read_plans(user_data: UserData = Depends(require_authentication)):
    # TODO: move logic to external method

    results = await prisma.query_raw(
        """
        SELECT * FROM "Plan"
        WHERE user_rut = $1
        LIMIT 50
        """,
        user_data.rut,
    )

    async def translate_plan_model(i: int):
        semesters = await prisma.query_raw(
            """
            SELECT * FROM "PlanSemester"
            WHERE plan_id = $1
            """,
            results[i]["id"],
        )

        plan_classes: list[list[str]] = []
        for s in semesters:
            plan_class = await prisma.query_raw(
                """
                SELECT class_code FROM "PlanClass"
                WHERE semester_id = $1
                """,
                s["id"],
            )
            plan_class_stripped = [p["class_code"] for p in plan_class]

            plan_classes.append(plan_class_stripped)

        return {
            "id": results[i]["id"],
            "created_at": results[i]["created_at"],
            "updated_at": results[i]["updated_at"],
            "name": results[i]["name"],
            "plan": ValidatablePlan(
                classes=plan_classes,
                next_semester=results[i]["next_semester"],
                level=Level(results[i]["level"]),
                school=results[i]["school"],
                program=results[i]["program"],
                career=results[i]["career"],
            ),
        }

    return [await translate_plan_model(i) for i in range(len(results))]


@app.put("/plan/stored")
async def update_plan(
    plan_id: str,
    new_plan: ValidatablePlan,
    user_data: UserData = Depends(require_authentication),
):
    # TODO: move logic to external method
    user_plans = await prisma.plan.find_many(where={"user_rut": user_data.rut})
    if plan_id not in [p.id for p in user_plans]:
        raise HTTPException(status_code=404, detail="Plan not found in user storage")

    # TODO: use PlanSemesterUpdateManyWithoutRelationsInput for nested relations update
    updated_plan = await prisma.plan.update(
        where={
            "id": plan_id,
        },
        data={
            # TODO --> "semesters": [["..."], ...],
            "next_semester": new_plan.next_semester,
            "level": new_plan.level,
            "school": new_plan.school,
            "program": new_plan.program,
            "career": new_plan.career,
        },
    )

    return updated_plan


@app.put("/plan/stored/name")
async def rename_plan(
    plan_id: str,
    new_name: str,
    user_data: UserData = Depends(require_authentication),
):
    # TODO: move logic to external method
    user_plans = await prisma.plan.find_many(where={"user_rut": user_data.rut})
    if plan_id not in [p.id for p in user_plans]:
        raise HTTPException(status_code=404, detail="Plan not found in user storage")

    updated_plan = await prisma.plan.update(
        where={
            "id": plan_id,
        },
        data={
            "name": new_name,
        },
    )

    return updated_plan


@app.delete("/plan/stored")
async def delete_plan():
    pass
