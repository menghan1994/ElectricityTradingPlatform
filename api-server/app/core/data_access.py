from dataclasses import dataclass
from uuid import UUID

import structlog
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import get_current_active_user
from app.core.exceptions import BusinessError
from app.models.user import User, UserRole
from app.repositories.binding import BindingRepository
from app.schemas.user import RoleType

logger = structlog.get_logger()


@dataclass(frozen=True)
class DataAccessContext:
    """数据访问上下文 — 通过 FastAPI Dependency 注入到 API 端点。

    约定：
    - station_ids=None → 全部可见（admin/trading_manager/executive_readonly）
    - station_ids=()   → 无权查看任何电站（trader 无绑定时）
    - device_ids=None  → 全部可见
    - device_ids=()    → 无权查看任何设备

    使用 tuple 而非 list 以确保 frozen=True 的不可变语义完整——
    list 仅阻止属性重赋值，但 .append() 仍可静默修改内容。
    """

    user_id: UUID
    role: RoleType
    station_ids: tuple[UUID, ...] | None  # None = 全部可见, () = 无权查看
    device_ids: tuple[UUID, ...] | None   # None = 全部可见, () = 无权查看

    @property
    def has_full_station_access(self) -> bool:
        return self.station_ids is None

    @property
    def has_full_device_access(self) -> bool:
        return self.device_ids is None

    @property
    def is_readonly(self) -> bool:
        return self.role == UserRole.EXECUTIVE_READONLY


async def get_data_access_context(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> DataAccessContext:
    """构建当前用户的数据访问上下文。

    按角色决定过滤策略：
    - admin/trading_manager/executive_readonly → 全部可见
    - trader → 仅已绑定电站
    - storage_operator → 仅已绑定设备 + 设备所属电站
    """
    binding_repo = BindingRepository(session)

    if current_user.role in (
        UserRole.ADMIN,
        UserRole.TRADING_MANAGER,
        UserRole.EXECUTIVE_READONLY,
    ):
        return DataAccessContext(
            user_id=current_user.id,
            role=current_user.role,
            station_ids=None,
            device_ids=None,
        )

    if current_user.role == UserRole.TRADER:
        station_ids = await binding_repo.get_user_station_ids(current_user.id)
        return DataAccessContext(
            user_id=current_user.id,
            role=current_user.role,
            station_ids=tuple(station_ids),
            device_ids=None,
        )

    if current_user.role == UserRole.STORAGE_OPERATOR:
        device_ids = await binding_repo.get_user_device_ids(current_user.id)
        station_ids = await binding_repo.get_user_device_station_ids(current_user.id)
        return DataAccessContext(
            user_id=current_user.id,
            role=current_user.role,
            station_ids=tuple(station_ids),
            device_ids=tuple(device_ids),
        )

    # 未知角色：零权限（安全降级）
    logger.warning(
        "unknown_role_zero_access",
        role=current_user.role,
        user_id=str(current_user.id),
    )
    return DataAccessContext(
        user_id=current_user.id,
        role=current_user.role,
        station_ids=(),
        device_ids=(),
    )


async def require_write_permission(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """拦截 executive_readonly 角色的写操作，返回 403。"""
    if current_user.role == UserRole.EXECUTIVE_READONLY:
        raise BusinessError(
            code="WRITE_PERMISSION_DENIED",
            message="只读角色无写操作权限",
            status_code=403,
        )
    return current_user
