from fastapi import APIRouter, Request
from fastapi_versionizer import api_version
from pydantic import BaseModel

from app.api.auth import auth_router
from app.api.user import user_router

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