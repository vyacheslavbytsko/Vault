from uuid import UUID

from fastapi import APIRouter, Depends
repo_router = APIRouter(prefix="/{user_id}/repo", tags=["Repositories"])

@repo_router.get("/{repo_id}")
async def get_user_repo(user_id: UUID, repo_id: UUID):
    return {"user_id": user_id, "repo_id": repo_id}