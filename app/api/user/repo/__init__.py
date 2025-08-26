from typing import Annotated

from fastapi import APIRouter, Depends, Form
from fastapi_versionizer import api_version

from app.core.auth import get_auth_context_access_token_fast
from app.models.user import User

repo_router = APIRouter(prefix="/me/repo", tags=["Repositories"])

@api_version(1, 0)
@repo_router.get("")
async def get_user_repos(
        auth_context: Annotated[User, Depends(get_auth_context_access_token_fast)]
):
    return ["123", "456"]


@api_version(1, 0)
@repo_router.post("")
async def create_repo(
        auth_context: Annotated[User, Depends(get_auth_context_access_token_fast)],
        repo_name: Annotated[str, Form()],
):
    return ["123", "456"]


@api_version(1, 0)
@repo_router.get("/{repo_id}")
async def get_info_about_user_repo(
        auth_context: Annotated[User, Depends(get_auth_context_access_token_fast)],
        repo_name: str):
    return {"repo_name": repo_name, "user": auth_context.model_dump()}