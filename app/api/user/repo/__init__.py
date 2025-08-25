from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Form
from fastapi_versionizer import api_version

from app.core.auth import get_current_user_access_token_fast
from app.models.user import User

repo_router = APIRouter(prefix="/me/repo", tags=["Repositories"])

@api_version(1, 0)
@repo_router.get("")
async def get_user_repos(current_user: Annotated[User, Depends(get_current_user_access_token_fast)]):
    return ["123", "456"]


@api_version(1, 0)
@repo_router.post("")
async def create_repo(
        current_user: Annotated[User, Depends(get_current_user_access_token_fast)],
        repo_name: Annotated[str, Form()],
):
    return ["123", "456"]


@api_version(1, 0)
@repo_router.get("/{repo_id}")
async def get_info_about_user_repo(
        current_user: Annotated[User, Depends(get_current_user_access_token_fast)],
        repo_name: str):
    return {"repo_name": repo_name, "user": current_user.model_dump()}