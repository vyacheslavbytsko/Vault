from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_versionizer import api_version

from app.api.user.repo import repo_router
from app.core.auth import get_current_user_access_token_fast
from app.models.user import UserPublic, User

user_router = APIRouter(prefix="/user")
user_router.include_router(repo_router)

@api_version(1, 0)
@user_router.get("/me", response_model=UserPublic, tags=["User"])
async def get_info_about_me(current_user: Annotated[User, Depends(get_current_user_access_token_fast)]):
    return current_user