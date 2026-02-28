from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.storage import StorageDevice
from app.repositories.base import BaseRepository


class StorageDeviceRepository(BaseRepository[StorageDevice]):
    def __init__(self, session: AsyncSession):
        super().__init__(StorageDevice, session)

    async def get_by_station_id(self, station_id: UUID) -> list[StorageDevice]:
        stmt = (
            select(StorageDevice)
            .where(StorageDevice.station_id == station_id, StorageDevice.is_active.is_(True))
            .order_by(StorageDevice.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_active(self) -> list[StorageDevice]:
        stmt = (
            select(StorageDevice)
            .where(StorageDevice.is_active.is_(True))
            .order_by(StorageDevice.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_ids(self, ids: list[UUID], *, active_only: bool = False) -> list[StorageDevice]:
        if not ids:
            return []
        stmt = select(StorageDevice).where(StorageDevice.id.in_(ids))
        if active_only:
            stmt = stmt.where(StorageDevice.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_active_filtered(
        self,
        allowed_device_ids: Sequence[UUID] | None = None,
        allowed_station_ids: Sequence[UUID] | None = None,
    ) -> list[StorageDevice]:
        """获取活跃设备，支持行级过滤。

        allowed_device_ids:
        - None → 不过滤（全部可见）
        - []   → 快速返回空结果
        - [id1, ...] → WHERE id IN (...) 过滤

        allowed_station_ids:
        - None → 不按电站过滤
        - []   → 快速返回空结果
        - [id1, ...] → WHERE station_id IN (...) 过滤（trader 场景：仅绑定电站下的设备）
        """
        if allowed_device_ids is not None and len(allowed_device_ids) == 0:
            return []
        if allowed_station_ids is not None and len(allowed_station_ids) == 0:
            return []

        stmt = (
            select(StorageDevice)
            .where(StorageDevice.is_active.is_(True))
            .order_by(StorageDevice.name)
        )
        if allowed_device_ids is not None:
            stmt = stmt.where(StorageDevice.id.in_(allowed_device_ids))
        if allowed_station_ids is not None:
            stmt = stmt.where(StorageDevice.station_id.in_(allowed_station_ids))

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
