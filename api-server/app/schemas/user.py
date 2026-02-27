from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

RoleType = Literal["admin", "trader", "storage_operator", "trading_manager", "executive_readonly"]


def _empty_str_to_none(v: str | None) -> str | None:
    """将空字符串转为 None，防止前端表单空值作为空字符串写入数据库。"""
    if v is not None and not v.strip():
        return None
    return v


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    display_name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    role: RoleType = "trader"
    is_active: bool
    is_locked: bool = False
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("email", mode="before")
    @classmethod
    def _coerce_empty_email(cls, v: str | None) -> str | None:
        return _empty_str_to_none(v)


class UserUpdate(BaseModel):
    display_name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None

    @field_validator("email", "display_name", "phone", mode="before")
    @classmethod
    def _coerce_empty_to_none(cls, v: str | None) -> str | None:
        return _empty_str_to_none(v)


class AdminUserCreate(BaseModel):
    # 有意允许大小写混合（如 "Admin123"），匹配企业用户名惯例
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$")
    display_name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    role: RoleType = "trader"

    @field_validator("email", "display_name", "phone", mode="before")
    @classmethod
    def _coerce_empty_to_none(cls, v: str | None) -> str | None:
        return _empty_str_to_none(v)


class AdminResetPasswordResponse(BaseModel):
    temp_password: str


class AdminCreateUserResponse(BaseModel):
    user: UserRead
    temp_password: str


class RoleAssignRequest(BaseModel):
    role: RoleType


class StatusToggleRequest(BaseModel):
    is_active: bool


class UserListResponse(BaseModel):
    items: list[UserRead]
    total: int
    page: int
    page_size: int
