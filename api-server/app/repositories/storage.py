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
