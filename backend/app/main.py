from .validate.validate import ValidatablePlan
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from .database import prisma
from prisma.models import Post
from prisma.types import PostCreateInput
from .auth import require_authentication, login_cas, UserData
from typing import Optional
from .coursesync import run_course_sync, universal_course_rules

app = FastAPI()


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


@app.on_event("shutdown")  # type: ignore
async def shutdown():
    await prisma.disconnect()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/posts")
async def get_posts():
    return await Post.prisma().find_many()


@app.put("/posts")
async def create_post(post: PostCreateInput):
    return await prisma.post.create(post)


@app.get("/auth")
async def authenticate(next: Optional[str] = None, ticket: Optional[str] = None):
    return await login_cas(next, ticket)


@app.get("/auth/check")
async def check_auth(userdata: UserData = Depends(require_authentication)):
    return {"message": "Authenticated"}


@app.post("/validate/sync")
# TODO: Require admin permissions for this endpoint.
async def course_sync():
    await run_course_sync()
    rules = await universal_course_rules()
    return {"message": f"Synchronized {len(rules.courses)} courses"}


# RESTfully we would use the GET method, but javascript can't send a body in a GET
# request.
@app.post("/validate")
async def validate_plan(plan: ValidatablePlan):
    rules = await universal_course_rules()
    diag = plan.diagnose(rules)
    return {"valid": len(diag) == 0, "diagnostic": diag}
