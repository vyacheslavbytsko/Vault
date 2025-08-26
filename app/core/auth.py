import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import get_vault_id
from app.core.db import get_db_async_session
from app.core.exceptions import HTTPCredentialsException
from app.models.session import Session, get_session_from_id
from app.models.user import User, get_user_from_username, get_user_from_id

_JWT_SECRET_KEY = None
JWT_ALGORITHM = "HS256"

password_hash = PasswordHash([Argon2Hasher()])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", refreshUrl="auth/refresh")


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
        token: Annotated[str, Depends(oauth2_scheme)]
) -> User | None:
    print("get_current_user_refresh_token")
    current_session = await get_current_session_refresh_token(db, token)
    if current_session is None:
        raise HTTPCredentialsException()
    return await get_user_from_id(db, current_session.user_id)


async def get_current_user_access_token_fast(
        db: Annotated[AsyncSession, Depends(get_db_async_session)],
        token: Annotated[str, Depends(oauth2_scheme)]
) -> User | None:
    print("get_current_user_access_token_fast")
    return await _get_current_user_access_token(db, token, True)


# maybe some day we will use this...
async def get_current_user_access_token_slow(
        db: Annotated[AsyncSession, Depends(get_db_async_session)],
        token: Annotated[str, Depends(oauth2_scheme)]
) -> User | None:
    print("get_current_user_access_token_slow")
    return await _get_current_user_access_token(db, token, False)


async def _get_current_user_access_token(
        db: Annotated[AsyncSession, Depends(get_db_async_session)],
        token: Annotated[str, Depends(oauth2_scheme)],
        fast: bool  # means without hitting db to get Session. still hits db to check if session_id is blocklisted (in development)
) -> User | None:
    print("_get_current_user_access_token")
    if fast:
        try:
            payload = decode_payload(token, "access")
            return await get_user_from_id(db, uuid.UUID(payload.get("sub")))
        except InvalidTokenError:
            raise HTTPCredentialsException()
    else:
        current_session = await get_current_session_access_token(db, token)
        if current_session is None:
            raise HTTPCredentialsException()
        return await get_user_from_id(db, current_session.user_id)


async def get_current_session_refresh_token(
        db: Annotated[AsyncSession, Depends(get_db_async_session)],
        token: Annotated[str, Depends(oauth2_scheme)]
) -> Session | None:
    print("get_current_session_refresh_token")
    return await _get_current_session(db, token, "refresh", True)


async def get_current_session_access_token(
        db: Annotated[AsyncSession, Depends(get_db_async_session)],
        token: Annotated[str, Depends(oauth2_scheme)]
) -> Session | None:
    print("get_current_session_access_token")
    return await _get_current_session(db, token, "access", False)


async def _get_current_session(
        db: Annotated[AsyncSession, Depends(get_db_async_session)],
        token: Annotated[str, Depends(oauth2_scheme)],
        token_type: str,
        check_jti: bool
) -> Session | None:
    print("_get_current_session")
    try:
        payload = decode_payload(token, token_type)
        session = await get_session_from_id(db, payload.get("session_id"))
        if check_jti:
            if uuid.UUID(payload.get("jti")) != session.jti:
                raise HTTPCredentialsException()
        return session
    except InvalidTokenError:
        raise HTTPCredentialsException()


async def refresh_session(
        db: Annotated[AsyncSession, Depends(get_db_async_session)],
        current_session: Annotated[Session, Depends(get_current_session_refresh_token)]
) -> tuple[Session | None, str | None, str | None]:
    print("refresh_session")
    user = await get_user_from_id(db, current_session.user_id)
    if not user:
        return None, None, None

    jti = uuid.uuid4()
    timestamp = datetime.now(timezone.utc)

    refresh_token = create_refresh_token(current_session.user_id, timestamp, jti, current_session.scope,
                                         current_session.id)
    current_session.jti = jti
    access_token = create_access_token(current_session.user_id, timestamp, current_session.scope, current_session.id)

    await db.commit()
    await db.refresh(current_session)
    return current_session, refresh_token, access_token


def decode_payload(token: str, token_type: str) -> dict[str, Any]:
    payload = jwt.decode(token, get_jwt_secret_key(), algorithms=[JWT_ALGORITHM])
    if payload.get("type") != token_type:
        raise HTTPCredentialsException()
    if payload.get("sub") is None:
        raise HTTPCredentialsException()
    return payload


"""async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user"""
