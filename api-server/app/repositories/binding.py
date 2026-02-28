from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.binding import UserDeviceBinding, UserStationBinding


class BindingRepository:
    """绑定关联表 Repository。

    设计决策：不继承 BaseRepository[T]，因为绑定表操作模式为"全量替换"
    （批量删除+批量插入），与 BaseRepository 的单实体 CRUD 模式不匹配。
    BindingRepository 管理两张关联表（UserStationBinding + UserDeviceBinding），
    无法用单一泛型参数表达。
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # ── 电站绑定 ──

    async def get_user_station_bindings(self, user_id: UUID) -> list[UserStationBinding]:
        stmt = select(UserStationBinding).where(UserStationBinding.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_station_ids(
        self, user_id: UUID, *, for_update: bool = False,
    ) -> list[UUID]:
        stmt = select(UserStationBinding.station_id).where(UserStationBinding.user_id == user_id)
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def replace_user_station_bindings(
        self, user_id: UUID, station_ids: list[UUID],
    ) -> list[UserStationBinding]:
        """全量替换用户的电站绑定关系"""
        # 删除现有绑定
        await self.session.execute(
            delete(UserStationBinding).where(UserStationBinding.user_id == user_id),
        )
        # 创建新绑定
        bindings = []
        for station_id in station_ids:
            binding = UserStationBinding(user_id=user_id, station_id=station_id)
            self.session.add(binding)
            bindings.append(binding)
        await self.session.flush()
        return bindings

    # ── 设备绑定 ──

    async def get_user_device_bindings(self, user_id: UUID) -> list[UserDeviceBinding]:
        stmt = select(UserDeviceBinding).where(UserDeviceBinding.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_device_ids(
        self, user_id: UUID, *, for_update: bool = False,
    ) -> list[UUID]:
        stmt = select(UserDeviceBinding.device_id).where(UserDeviceBinding.user_id == user_id)
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def replace_user_device_bindings(
        self, user_id: UUID, device_ids: list[UUID],
    ) -> list[UserDeviceBinding]:
        """全量替换用户的设备绑定关系"""
        await self.session.execute(
            delete(UserDeviceBinding).where(UserDeviceBinding.user_id == user_id),
        )
        bindings = []
        for device_id in device_ids:
            binding = UserDeviceBinding(user_id=user_id, device_id=device_id)
            self.session.add(binding)
            bindings.append(binding)
        await self.session.flush()
        return bindings

    # ── 查询辅助 ──

    async def get_station_binding_count(self, station_id: UUID) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(UserStationBinding).where(
            UserStationBinding.station_id == station_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
