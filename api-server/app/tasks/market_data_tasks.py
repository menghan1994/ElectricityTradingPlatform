import asyncio
from datetime import date, timezone

import structlog
from sqlalchemy import select

from app.core.database import get_sync_session_factory
from app.models.market_data import MarketDataSource
from app.services.market_data_adapters import get_adapter
from app.services.market_data_adapters.base import MarketPriceRecord
from app.tasks.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="app.tasks.market_data_tasks.fetch_market_data_periodic")
def fetch_market_data_periodic() -> dict:
    """Celery beat 定时任务：遍历所有活跃数据源，逐省份获取市场数据。

    使用同步会话包裹异步适配器调用。
    """
    session_factory = get_sync_session_factory()
    results: dict[str, str] = {}

    with session_factory() as session:
        stmt = select(MarketDataSource).where(MarketDataSource.is_active.is_(True))
        sources = list(session.execute(stmt).scalars().all())

        if not sources:
            logger.info("market_data_periodic_no_active_sources")
            return {"status": "no_active_sources"}

        today = date.today()

        for source in sources:
            province = source.province
            try:
                api_key = None
                if source.api_key_encrypted:
                    from app.services.market_data_service import _decrypt_api_key
                    api_key = _decrypt_api_key(source.api_key_encrypted)

                if not source.api_endpoint:
                    logger.warning(
                        "market_data_periodic_no_endpoint",
                        province=province,
                    )
                    results[province] = "skipped_no_endpoint"
                    continue

                adapter = get_adapter(
                    api_endpoint=source.api_endpoint,
                    api_key=api_key,
                    api_auth_type=source.api_auth_type,
                )

                # 在事件循环中运行异步适配器
                records = asyncio.run(adapter.fetch(today))

                # 使用同步方式写入数据库
                from datetime import datetime, UTC
                from sqlalchemy.dialects.postgresql import insert as pg_insert
                from app.models.market_data import MarketClearingPrice

                now = datetime.now(UTC)
                db_records = [
                    {
                        "trading_date": r.trading_date,
                        "period": r.period,
                        "province": province,
                        "clearing_price": r.clearing_price,
                        "source": "api",
                        "fetched_at": now,
                    }
                    for r in records
                ]

                if db_records:
                    insert_stmt = pg_insert(MarketClearingPrice).values(db_records)
                    insert_stmt = insert_stmt.on_conflict_do_update(
                        index_elements=["province", "trading_date", "period"],
                        set_={
                            "clearing_price": insert_stmt.excluded.clearing_price,
                            "source": insert_stmt.excluded.source,
                            "fetched_at": insert_stmt.excluded.fetched_at,
                        },
                    )
                    session.execute(insert_stmt)

                # 更新数据源状态
                source.last_fetch_at = now
                source.last_fetch_status = "success"
                source.last_fetch_error = None
                session.commit()

                results[province] = f"success:{len(records)}"
                logger.info(
                    "market_data_periodic_fetched",
                    province=province,
                    records_count=len(records),
                )

            except Exception as e:
                session.rollback()
                # 更新失败状态
                try:
                    source.last_fetch_status = "failed"
                    source.last_fetch_error = str(e)[:500]
                    session.commit()
                except Exception:
                    session.rollback()

                results[province] = f"failed:{e}"
                logger.warning(
                    "market_data_periodic_failed",
                    province=province,
                    error=str(e),
                )

    return results
