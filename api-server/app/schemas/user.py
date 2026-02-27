from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    display_name: str | None = None
    phone: str | None = None
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str | None = None
    phone: str | None = None


class UserUpdate(BaseModel):
    display_name: str | None = None
    phone: str | None = None
