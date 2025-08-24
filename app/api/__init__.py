from typing import Annotated

from fastapi import APIRouter, Request, Depends
from fastapi_versionizer import api_version
from pydantic import BaseModel

from app.api.auth import auth_router
from app.api.user import user_router
from app.core.auth import User, get_current_user_access_token
from app.models.user import UserPublic

api_router = APIRouter()
api_router.include_router(user_router)
api_router.include_router(auth_router)


class Ping(BaseModel):
    ping: str = "pong"
    versions: list[str] = ["v1.0"]

@api_version(1, 0)
@api_router.get('/ping', tags=['Common'])
async def ping(request: Request) -> Ping:
    return Ping(
        ping="pong",
        versions=request.app.state.versions
    )

"""@api_version(1, 0)
@api_router.get("/users/me", response_model=UserPublic)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_user_access_token)],
):
    return current_user


@api_version(1, 0)
@api_router.get("/users/me/items")
async def read_own_items(
    current_user: Annotated[User, Depends(get_current_user_access_token)],
):
    return [{"item_id": "Foo", "owner": current_user.username}]"""