from datetime import datetime
from uuid import UUID

from sqlmodel import SQLModel, Field


class Session(SQLModel, table=True):
    __tablename__ = "BVSessions"

    user_id: UUID = Field(nullable=False, index=True, foreign_key="BVUsers.id")
    id: UUID = Field(primary_key=True, nullable=False, index=True)
    name: str = Field(nullable=True)
    jti: UUID = Field(unique=True, nullable=False)
    scope: str = Field(nullable=False)
    created_at: datetime = Field(nullable=False)  # just for info
    updated_at: datetime = Field(nullable=False)  # is used to remove session if it is expired

    #user: Mapped[User] = relationship(User)
