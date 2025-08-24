from uuid import UUID

from sqlmodel import SQLModel, Field, select
from sqlmodel.ext.asyncio.session import AsyncSession


class UserBase(SQLModel):
    id: UUID = Field(primary_key=True, nullable=False, index=True)
    username: str = Field(nullable=False, unique=True, index=True)


class User(UserBase, table=True):
    __tablename__ = "BVUsers"

    password: str | None = Field(nullable=True)


class UserPublic(UserBase):
    pass


async def get_user_from_username(db: AsyncSession, username: str) -> User:
    user = (await db.scalar(select(User).where(User.username == username)))
    return user


async def get_user_from_id(db: AsyncSession, user_id: str) -> User:
    user = (await db.scalar(select(User).where(User.id == UUID(user_id))))
    return user