from fastapi import APIRouter

from app.api.user.repo import repo_router

user_router = APIRouter(prefix="/user")
user_router.include_router(repo_router)