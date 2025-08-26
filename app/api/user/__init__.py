from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_versionizer import api_version

from app.api.user.repo import repo_router
from app.core.auth import get_auth_context_access_token_fast, AuthContext
from app.models.user import UserPublic, User

user_router = APIRouter(prefix="/user")
user_router.include_router(repo_router)

@api_version(1, 0)
@user_router.get("/me", response_model=UserPublic, tags=["User"])
async def get_info_about_me(auth_context: Annotated[AuthContext, Depends(get_auth_context_access_token_fast)]):
    return auth_context.user