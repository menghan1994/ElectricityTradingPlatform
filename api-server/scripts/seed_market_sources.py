"""种子数据脚本 — 为常用省份创建市场数据源配置（指向 Mock API）

用法：
    docker compose -f docker-compose.yml -f docker-compose.dev.yml \
        exec api-server python -m scripts.seed_market_sources

幂等：按 province 判断，已存在则跳过。
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.market_data import MarketDataSource

# ---------------------------------------------------------------------------
# 配置区
# ---------------------------------------------------------------------------

MOCK_API_ENDPOINT = "http://mock-market-api:8080/market-data"

SOURCES = [
    {"province": "guangdong", "source_name": "广东电力交易中心（Mock）"},
    {"province": "shandong", "source_name": "山东电力交易中心（Mock）"},
    {"province": "jiangsu", "source_name": "江苏电力交易中心（Mock）"},
    {"province": "zhejiang", "source_name": "浙江电力交易中心（Mock）"},
    {"province": "hebei", "source_name": "河北电力交易中心（Mock）"},
    {"province": "neimenggu", "source_name": "内蒙古电力交易中心（Mock）"},
    {"province": "gansu", "source_name": "甘肃电力交易中心（Mock）"},
    {"province": "xinjiang", "source_name": "新疆电力交易中心（Mock）"},
]


async def seed() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        created = 0
        skipped = 0

        for src in SOURCES:
            result = await session.execute(
                select(MarketDataSource).where(
                    MarketDataSource.province == src["province"],
                ),
            )
            existing = result.scalar_one_or_none()
            if existing:
                print(f"  跳过  {src['source_name']}（province={src['province']} 已存在）")
                skipped += 1
            else:
                source = MarketDataSource(
                    province=src["province"],
                    source_name=src["source_name"],
                    api_endpoint=MOCK_API_ENDPOINT,
                    api_auth_type="none",
                    fetch_schedule="0 7,12,17 * * *",
                    is_active=True,
                    cache_ttl_seconds=3600,
                )
                session.add(source)
                print(f"  创建  {src['source_name']}  → {MOCK_API_ENDPOINT}")
                created += 1

        await session.commit()
        print(f"\n完成: 数据源 {created} 个新建 / {skipped} 个跳过。")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
