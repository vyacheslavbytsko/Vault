from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_versionizer import api_version
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette import status

from app.core.auth import log_in_user_via_credentials, register_user_with_credentials, \
    get_current_session_refresh_token, refresh_session
from app.core.db import get_db_async_session
from app.core.exceptions import HTTPUserAlreadyCreatedException, HTTPCredentialsException
from app.models.session import Session
from app.models.user import get_user_from_username

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


class Token(BaseModel):
    refresh_token: str
    access_token: str
    token_type: str


@api_version(1, 0)
@auth_router.post("/register")
async def register(
        username: Annotated[str, Form()],
        password: Annotated[str, Form()],
        session: Annotated[AsyncSession, Depends(get_db_async_session)]
) -> Token:
    if await get_user_from_username(session, username) is not None:
        raise HTTPUserAlreadyCreatedException()

    session, refresh_token, access_token = await register_user_with_credentials(session, username, password)
    return Token(
        refresh_token=refresh_token,
        access_token=access_token,
        token_type="bearer")


@api_version(1, 0)
@auth_router.post("/login")
async def login(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        db: Annotated[AsyncSession, Depends(get_db_async_session)]
) -> Token:
    session, refresh_token, access_token = await log_in_user_via_credentials(db, form_data.username, form_data.password)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Token(
        refresh_token=refresh_token,
        access_token=access_token,
        token_type="bearer")


@api_version(1, 0)
@auth_router.get("/refresh")
async def refresh(
        current_session: Annotated[Session, Depends(get_current_session_refresh_token)],
        db: Annotated[AsyncSession, Depends(get_db_async_session)]
) -> Token:
    session, refresh_token, access_token = await refresh_session(db, current_session)

    if not session:
        raise HTTPCredentialsException()

    return Token(
        refresh_token=refresh_token,
        access_token=access_token,
        token_type="bearer")

