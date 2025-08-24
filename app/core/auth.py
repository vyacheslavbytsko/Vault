import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette import status
from starlette.exceptions import HTTPException

from app.core import get_vault_id
from app.core.db import get_db_async_session
from app.models.session import Session
from app.models.user import User, get_user_from_username, get_user_from_id

_JWT_SECRET_KEY = None
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

password_hash = PasswordHash([Argon2Hasher()])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_jwt_secret_key() -> str:
    global _JWT_SECRET_KEY
    if _JWT_SECRET_KEY is None:
        if not os.path.isfile("data/JWT_SECRET_KEY"):
            with open("data/JWT_SECRET_KEY", "w") as f:
                f.write(os.urandom(512).hex())
        _JWT_SECRET_KEY = open("data/JWT_SECRET_KEY").read().strip()
    return _JWT_SECRET_KEY


def verify_password(plain_password, hashed_password):
    # TODO: verify_and_update
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password):
    return password_hash.hash(password)


async def register_user_with_credentials(
        db: AsyncSession, username: str, password: str) -> tuple[Session, str, str]:
    if await get_user_from_username(db, username) is not None:
        raise Exception(f"User {username} already exists")
    user = User(
        id=uuid.uuid4(),
        username=username,
        password=get_password_hash(password),
        is_active=True,
        # TODO: change fast login secret
        fast_login_secret="123"
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return await create_session(db, user.id, None, "all")


async def log_in_user_via_credentials(db: AsyncSession, username: str, password: str) -> tuple[Session | None, str | None, str | None]:
    user = await get_user_from_username(db, username)
    if not user:
        return None, None, None
    if not verify_password(password, user.password):
        return None, None, None
    return await create_session(db, user.id, None, "all")


async def create_session(db: AsyncSession, user_id: uuid.UUID, name: str | None, scope: str) -> tuple[Session, str, str]:
    session_id = uuid.uuid4()
    jti = uuid.uuid4()
    timestamp = datetime.now(timezone.utc)

    refresh_token = create_refresh_token(user_id, timestamp, jti, scope, session_id)

    session = Session(
        user_id=user_id,
        id=session_id,
        name=name,
        jti=jti,
        scope=scope,
        created_at=timestamp,
        updated_at=timestamp
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    access_token = create_access_token(user_id, timestamp, scope, session_id)
    return session, refresh_token, access_token


def create_refresh_token(user_id: uuid.UUID, iat: datetime | None, jti: uuid.UUID, scope: str,
                         session_id: uuid.UUID) -> str:
    refresh_token_expires = timedelta(days=365)
    iat = iat or datetime.now(timezone.utc)

    payload = {
        "iss": get_vault_id(),
        "sub": str(user_id),
        "exp": iat + refresh_token_expires,
        "iat": iat,
        "jti": str(jti),
        "type": "refresh",
        "scope": scope,
        "session_id": str(session_id)
    }

    encoded_jwt = jwt.encode(payload, get_jwt_secret_key(), algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_access_token(user_id: uuid.UUID, iat: datetime | None, scope: str, session_id: uuid.UUID) -> str:
    access_token_expires = timedelta(hours=1)
    iat = iat or datetime.now(timezone.utc)

    payload = {
        "iss": get_vault_id(),
        "sub": str(user_id),
        "exp": iat + access_token_expires,
        "iat": iat,
        "type": "access",
        "scope": scope,
        "session_id": str(session_id)  # TODO: create db table with blocklisted session ids
    }

    encoded_jwt = jwt.encode(payload, get_jwt_secret_key(), algorithm=JWT_ALGORITHM)
    return encoded_jwt


async def get_current_user_refresh_token(
        db: Annotated[AsyncSession, Depends(get_db_async_session)],
        token: Annotated[str, Depends(oauth2_scheme)]):
    return await _get_current_user(db, token, "refresh")


async def get_current_user_access_token(
        db: Annotated[AsyncSession, Depends(get_db_async_session)],
        token: Annotated[str, Depends(oauth2_scheme)]):
    return await _get_current_user(db, token, "access")


async def _get_current_user(db: AsyncSession, token: str, token_type: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, get_jwt_secret_key(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != token_type:
            raise credentials_exception
        if payload.get("sub") is None:
            raise credentials_exception
        return await get_user_from_id(db, payload.get("sub"))
    except InvalidTokenError:
        raise credentials_exception

"""async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user"""
