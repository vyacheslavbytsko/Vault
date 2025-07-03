from fastapi import APIRouter, Depends, Request
from fastapi_versionizer import api_version

from vault.entities.user.manager import fastapi_users, auth_backend, current_active_user
from vault.entities.user.model import User
from vault.entities.user.schema import UserRead, UserCreate, UserUpdate

api_router = APIRouter(
    prefix='',
)

api_router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["Auth"]
)

api_router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["Auth"],
)
"""api_router.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["Auth"],
)"""
api_router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/user",
    tags=["Users"],
)

"""@api_version(1, 0)
@api_router.get("/authenticated-route")
async def authenticated_route(user: User = Depends(current_active_user)):
    return {"message": f"Hello {user.email}!"}"""


@api_version(1, 0)
@api_router.get('/ping', tags=['Common'])
def ping(request: Request) -> dict:
    return {"ping": "pong", "latest": request.app.state.latest_api_version}