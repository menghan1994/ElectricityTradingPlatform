from datetime import date, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data import MarketClearingPrice, MarketDataSource
from app.repositories.base import BaseRepository


class MarketClearingPriceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_upsert(self, records: list[dict]) -> int:
        if not records:
            return 0
        stmt = pg_insert(MarketClearingPrice).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=["province", "trading_date", "period"],
            set_={
                "clearing_price": stmt.excluded.clearing_price,
                "source": stmt.excluded.source,
                "fetched_at": stmt.excluded.fetched_at,
                "import_job_id": stmt.excluded.import_job_id,
            },
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def get_by_province_date(
        self,
        province: str,
        trading_date: date,
        page: int = 1,
        page_size: int = 96,
    ) -> tuple[list[MarketClearingPrice], int]:
        page_size = min(page_size, 100)

        count_stmt = (
            select(func.count())
            .select_from(MarketClearingPrice)
            .where(
                MarketClearingPrice.province == province,
                MarketClearingPrice.trading_date == trading_date,
            )
        )
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(MarketClearingPrice)
            .where(
                MarketClearingPrice.province == province,
                MarketClearingPrice.trading_date == trading_date,
            )
            .order_by(MarketClearingPrice.period)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        records = list(result.scalars().all())
        return records, total

    async def get_latest_by_province(self, province: str) -> MarketClearingPrice | None:
        stmt = (
            select(MarketClearingPrice)
            .where(MarketClearingPrice.province == province)
            .order_by(
                MarketClearingPrice.trading_date.desc(),
                MarketClearingPrice.period.desc(),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def check_freshness(self, province: str) -> datetime | None:
        stmt = (
            select(func.max(MarketClearingPrice.fetched_at))
            .where(MarketClearingPrice.province == province)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        province: str | None = None,
        trading_date: date | None = None,
        page: int = 1,
        page_size: int = 96,
    ) -> tuple[list[MarketClearingPrice], int]:
        page_size = min(page_size, 100)

        stmt = select(MarketClearingPrice)
        count_stmt = select(func.count()).select_from(MarketClearingPrice)

        if province:
            stmt = stmt.where(MarketClearingPrice.province == province)
            count_stmt = count_stmt.where(MarketClearingPrice.province == province)

        if trading_date:
            stmt = stmt.where(MarketClearingPrice.trading_date == trading_date)
            count_stmt = count_stmt.where(MarketClearingPrice.trading_date == trading_date)

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            stmt.order_by(
                MarketClearingPrice.trading_date.desc(),
                MarketClearingPrice.period,
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        records = list(result.scalars().all())
        return records, total


class MarketDataSourceRepository(BaseRepository[MarketDataSource]):
    def __init__(self, session: AsyncSession):
        super().__init__(MarketDataSource, session)

    async def get_by_province(self, province: str) -> MarketDataSource | None:
        stmt = select(MarketDataSource).where(MarketDataSource.province == province)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_sources(self) -> list[MarketDataSource]:
        stmt = (
            select(MarketDataSource)
            .where(MarketDataSource.is_active.is_(True))
            .order_by(MarketDataSource.province)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_fetch_status(
        self,
        source_id: UUID,
        status: str,
        error_message: str | None = None,
        last_fetch_at: datetime | None = None,
    ) -> None:
        values: dict = {"last_fetch_status": status}
        if error_message is not None:
            values["last_fetch_error"] = error_message
        if last_fetch_at is not None:
            values["last_fetch_at"] = last_fetch_at
        stmt = (
            update(MarketDataSource)
            .where(MarketDataSource.id == source_id)
            .values(**values)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def list_all_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
    ) -> tuple[list[MarketDataSource], int]:
        page_size = min(page_size, 100)

        stmt = select(MarketDataSource)
        count_stmt = select(func.count()).select_from(MarketDataSource)

        if is_active is not None:
            stmt = stmt.where(MarketDataSource.is_active == is_active)
            count_stmt = count_stmt.where(MarketDataSource.is_active == is_active)

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            stmt.order_by(MarketDataSource.province)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        sources = list(result.scalars().all())
        return sources, total
