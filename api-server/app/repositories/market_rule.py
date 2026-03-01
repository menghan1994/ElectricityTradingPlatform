from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_rule import ProvinceMarketRule
from app.repositories.base import BaseRepository


class MarketRuleRepository(BaseRepository[ProvinceMarketRule]):
    def __init__(self, session: AsyncSession):
        super().__init__(ProvinceMarketRule, session)

    async def get_by_province(self, province: str) -> ProvinceMarketRule | None:
        stmt = select(ProvinceMarketRule).where(
            ProvinceMarketRule.province == province
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_province_for_update(self, province: str) -> ProvinceMarketRule | None:
        stmt = (
            select(ProvinceMarketRule)
            .where(ProvinceMarketRule.province == province)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all_active(self) -> list[ProvinceMarketRule]:
        stmt = (
            select(ProvinceMarketRule)
            .where(ProvinceMarketRule.is_active.is_(True))
            .order_by(ProvinceMarketRule.province)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
