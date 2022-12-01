from fastapi import FastAPI
from .database import prisma
from prisma.models import Post
from prisma.types import PostCreateInput


app = FastAPI()


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
