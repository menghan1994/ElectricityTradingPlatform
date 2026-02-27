from datetime import datetime
from typing import get_args

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin
from app.schemas.user import RoleType


class UserRole:
    ADMIN = "admin"
    TRADER = "trader"
    STORAGE_OPERATOR = "storage_operator"
    TRADING_MANAGER = "trading_manager"
    EXECUTIVE_READONLY = "executive_readonly"

    # 从 RoleType Literal 自动生成，消除双源真值问题
    ALL: frozenset[str] = frozenset(get_args(RoleType))


class User(Base, IdMixin, TimestampMixin):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True,
    )
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(64))
    phone: Mapped[str | None] = mapped_column(String(20))
    # email 允许 NULL + unique：PostgreSQL 允许多行 NULL（NULL != NULL），
    # 即多个用户可以没有邮箱，但非 NULL 邮箱必须唯一。这是有意设计。
    email: Mapped[str | None] = mapped_column(String(128), unique=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=UserRole.TRADER)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
