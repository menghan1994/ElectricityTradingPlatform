from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.station import PowerStation
from app.repositories.base import BaseRepository


class StationRepository(BaseRepository[PowerStation]):
    def __init__(self, session: AsyncSession):
        super().__init__(PowerStation, session)

    async def get_by_name(self, name: str, *, active_only: bool = True) -> PowerStation | None:
        """MEDIUM: 默认仅查活跃电站，允许已停用名称被新电站使用。"""
        stmt = select(PowerStation).where(PowerStation.name == name)
        if active_only:
            stmt = stmt.where(PowerStation.is_active.is_(True))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_active(self) -> list[PowerStation]:
        stmt = (
            select(PowerStation)
            .where(PowerStation.is_active.is_(True))
            .order_by(PowerStation.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_province(self, province: str) -> list[PowerStation]:
        stmt = (
            select(PowerStation)
            .where(PowerStation.province == province, PowerStation.is_active.is_(True))
            .order_by(PowerStation.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_ids(self, ids: list[UUID], *, active_only: bool = False) -> list[PowerStation]:
        if not ids:
            return []
        stmt = select(PowerStation).where(PowerStation.id.in_(ids))
        if active_only:
            stmt = stmt.where(PowerStation.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def has_active_bindings(self, station_id: UUID) -> bool:
        """检查电站是否有绑定关系（含所有用户，不论用户是否活跃）。

        设计决策：不过滤已停用用户的绑定记录。原因：
        - 已停用用户可能被重新启用，此时绑定关系应自动恢复
        - 绑定清理应在停用用户的业务流程中显式处理，而非在电站侧隐式忽略
        - 若需忽略已停用用户的绑定，应在停用用户时同步清理绑定记录
        """
        from app.models.binding import UserStationBinding

        stmt = select(func.count()).select_from(UserStationBinding).where(
            UserStationBinding.station_id == station_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def get_all_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        province: str | None = None,
        station_type: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[PowerStation], int]:
        return await self.get_all_paginated_filtered(
            page=page,
            page_size=page_size,
            search=search,
            province=province,
            station_type=station_type,
            is_active=is_active,
        )

    async def get_all_paginated_filtered(
        self,
        allowed_station_ids: Sequence[UUID] | None = None,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        province: str | None = None,
        station_type: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[PowerStation], int]:
        """分页查询电站，支持行级数据过滤。

        allowed_station_ids:
        - None → 不过滤（全部可见）
        - []   → 快速返回空结果（无权查看）
        - [id1, id2, ...] → WHERE id IN (...) 过滤
        """
        if allowed_station_ids is not None and len(allowed_station_ids) == 0:
            return [], 0

        page_size = min(page_size, 100)
        stmt = select(PowerStation)
        count_stmt = select(func.count()).select_from(PowerStation)

        # 核心：行级数据过滤
        if allowed_station_ids is not None:
            stmt = stmt.where(PowerStation.id.in_(allowed_station_ids))
            count_stmt = count_stmt.where(PowerStation.id.in_(allowed_station_ids))

        if is_active is not None:
            stmt = stmt.where(PowerStation.is_active.is_(is_active))
            count_stmt = count_stmt.where(PowerStation.is_active.is_(is_active))

        if search:
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            search_filter = PowerStation.name.ilike(f"%{escaped}%", escape="\\")
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        if province:
            stmt = stmt.where(PowerStation.province == province)
            count_stmt = count_stmt.where(PowerStation.province == province)

        if station_type:
            stmt = stmt.where(PowerStation.station_type == station_type)
            count_stmt = count_stmt.where(PowerStation.station_type == station_type)

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.order_by(PowerStation.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        stations = list(result.scalars().all())

        return stations, total

    async def get_all_active_filtered(
        self,
        allowed_station_ids: Sequence[UUID] | None = None,
    ) -> list[PowerStation]:
        """获取活跃电站，支持行级过滤。"""
        if allowed_station_ids is not None and len(allowed_station_ids) == 0:
            return []

        stmt = (
            select(PowerStation)
            .where(PowerStation.is_active.is_(True))
            .order_by(PowerStation.name)
        )
        if allowed_station_ids is not None:
            stmt = stmt.where(PowerStation.id.in_(allowed_station_ids))

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
