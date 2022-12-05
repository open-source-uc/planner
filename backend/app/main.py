from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from .database import prisma
from prisma.models import Post
from prisma.types import PostCreateInput
from typing import Optional, Any
from cas import CASClient
from .consts import Consts
from jose import jwt
from datetime import datetime, timedelta

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


cas_client = CASClient(
    version=3,
    service_url="http://localhost:8000/login?next=%2F",
    server_url="http://localhost:3004/",
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


def generate_token(user: str, rut: str, expire_delta: Optional[int] = None):
    if expire_delta is None:
        expire_delta = Consts.default_login_expire
    expire_time = datetime.utcnow() + timedelta(seconds=expire_delta)
    payload = {"exp": expire_time, "sub": user, "rut": rut}
    jwt_token = jwt.encode(payload, Consts.Jwt.secret, Consts.Jwt.algorithm)
    return jwt_token


@app.get("/login")
async def login_cas(
    request: Request, next: Optional[str] = None, ticket: Optional[str] = None
):
    next = Consts.Frontend.login_success

    if not ticket:
        # Request comes from the user browser, redirect to CAS login
        cas_login_url: str = cas_client.get_login_url()
        print(f'cas_login_url = "{cas_login_url}"')
        return RedirectResponse(cas_login_url)

    # Receiving a CAS callback
    print(f'ticket = "{ticket}"')
    print(f'next = "{next}"')
    user: Any
    attributes: Any
    pgtiou: Any
    user, attributes, pgtiou = cas_client.verify_ticket(ticket)
    print(
        "CAS verify response: "
        f'user = "{user}", attributes = "{attributes}", pgtiou = "{pgtiou}"'
    )
    if not user:
        # Failed to authenticate
        return RedirectResponse(Consts.Frontend.login_fail)

    # Generate JWT token
    jwt_token = generate_token(user, attributes["carlicense"])
    res = RedirectResponse(next + f"?jwt={jwt_token}")
    return res
