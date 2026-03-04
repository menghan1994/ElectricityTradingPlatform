import json
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import redis.asyncio as aioredis
import structlog

from app.core.config import settings
from app.core.exceptions import BusinessError
from app.models.market_data import MarketDataSource
from app.repositories.market_data import (
    MarketClearingPriceRepository,
    MarketDataSourceRepository,
)
from app.schemas.market_data import FreshnessStatus, MarketDataFreshness
from app.services.audit_service import AuditService
from app.services.market_data_adapters import get_adapter
from app.services.market_data_adapters.base import MarketPriceRecord

logger = structlog.get_logger()

CACHE_PREFIX = "market_data"
FRESHNESS_THRESHOLDS_HOURS = {
    "fresh": 2,
    "stale": 12,
    "expired": 24,
}


def _get_fernet():
    """获取 Fernet 加密实例（基于 MARKET_DATA_ENCRYPTION_KEY 派生密钥）。"""
    import base64
    import hashlib
    from cryptography.fernet import Fernet

    key_bytes = hashlib.sha256(settings.MARKET_DATA_ENCRYPTION_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def _encrypt_api_key(api_key: str) -> bytes:
    """使用 Fernet (AES-128-CBC + HMAC-SHA256) 对称加密 API Key。"""
    f = _get_fernet()
    return f.encrypt(api_key.encode())


def _decrypt_api_key(encrypted: bytes) -> str:
    """解密 API Key。"""
    f = _get_fernet()
    return f.decrypt(encrypted).decode()


class MarketDataService:
    def __init__(
        self,
        price_repo: MarketClearingPriceRepository,
        source_repo: MarketDataSourceRepository,
        audit_service: AuditService,
        redis_client: aioredis.Redis | None = None,
    ):
        self.price_repo = price_repo
        self.source_repo = source_repo
        self.audit_service = audit_service
        self.redis_client = redis_client

    # --- 数据获取 ---

    async def fetch_market_data(
        self,
        province: str,
        trading_date: date,
        user_id: UUID | None = None,
    ) -> list[MarketPriceRecord]:
        """从外部 API 获取96时段出清价格并存储。"""
        source = await self.source_repo.get_by_province(province)
        if not source:
            raise BusinessError(
                code="SOURCE_NOT_FOUND",
                message=f"未找到省份 {province} 的数据源配置",
            )
        if not source.api_endpoint:
            raise BusinessError(
                code="SOURCE_NO_ENDPOINT",
                message=f"省份 {province} 的数据源未配置API端点",
            )

        api_key = None
        if source.api_key_encrypted:
            api_key = _decrypt_api_key(source.api_key_encrypted)

        adapter = get_adapter(
            api_endpoint=source.api_endpoint,
            api_key=api_key,
            api_auth_type=source.api_auth_type,
        )

        try:
            records = await adapter.fetch(trading_date)
        except Exception as e:
            await self.source_repo.update_fetch_status(
                source.id, "failed", error_message=str(e),
            )
            logger.warning(
                "market_data_fetch_failed",
                province=province,
                trading_date=trading_date.isoformat(),
                error=str(e),
            )
            raise BusinessError(
                code="FETCH_FAILED",
                message=f"市场数据获取失败: {e}",
            )

        # 写入数据库
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
        count = await self.price_repo.bulk_upsert(db_records)

        # 更新 Redis 缓存
        await self._set_cache(province, trading_date, records, source.cache_ttl_seconds)

        # 更新数据源状态
        await self.source_repo.update_fetch_status(
            source.id, "success", last_fetch_at=now,
        )

        # 审计日志
        if user_id:
            await self.audit_service.log_action(
                user_id=user_id,
                action="fetch_market_data",
                resource_type="market_clearing_price",
                resource_id=source.id,
                changes_after={
                    "province": province,
                    "trading_date": trading_date.isoformat(),
                    "records_count": count,
                },
            )

        logger.info(
            "market_data_fetched",
            province=province,
            trading_date=trading_date.isoformat(),
            records_count=count,
        )
        return records

    async def get_market_data(
        self,
        province: str,
        trading_date: date,
    ) -> list[dict]:
        """获取市场数据：Redis 缓存 → DB → API 获取。"""
        # Level 1: Redis 缓存
        cached = await self._get_cache(province, trading_date)
        if cached is not None:
            return cached

        # Level 2: 数据库查询
        records, _ = await self.price_repo.get_by_province_date(province, trading_date)
        if records:
            record_dicts = [
                {
                    "period": r.period,
                    "clearing_price": str(r.clearing_price),
                    "source": r.source,
                    "fetched_at": r.fetched_at.isoformat(),
                }
                for r in records
            ]
            # 回填缓存
            source = await self.source_repo.get_by_province(province)
            ttl = source.cache_ttl_seconds if source else settings.MARKET_DATA_DEFAULT_CACHE_TTL
            await self._set_cache_raw(province, trading_date, record_dicts, ttl)
            return record_dicts

        # Level 3: 触发 API 获取
        try:
            fetched = await self.fetch_market_data(province, trading_date)
            return [
                {
                    "period": r.period,
                    "clearing_price": str(r.clearing_price),
                    "source": "api",
                    "fetched_at": datetime.now(UTC).isoformat(),
                }
                for r in fetched
            ]
        except BusinessError:
            # Level 4: 获取失败，返回空
            return []

    # --- 数据新鲜度 ---

    async def check_data_freshness(self, province: str) -> MarketDataFreshness:
        """检查指定省份的数据新鲜度。"""
        last_updated = await self.price_repo.check_freshness(province)
        if last_updated is None:
            return MarketDataFreshness(
                province=province,
                last_updated=None,
                hours_ago=None,
                status="critical",
            )

        now = datetime.now(UTC)
        if last_updated.tzinfo is None:
            hours_ago = (now.replace(tzinfo=None) - last_updated).total_seconds() / 3600
        else:
            hours_ago = (now - last_updated).total_seconds() / 3600

        status: FreshnessStatus
        if hours_ago < FRESHNESS_THRESHOLDS_HOURS["fresh"]:
            status = "fresh"
        elif hours_ago < FRESHNESS_THRESHOLDS_HOURS["stale"]:
            status = "stale"
        elif hours_ago < FRESHNESS_THRESHOLDS_HOURS["expired"]:
            status = "expired"
        else:
            status = "critical"

        return MarketDataFreshness(
            province=province,
            last_updated=last_updated,
            hours_ago=round(hours_ago, 1),
            status=status,
        )

    async def check_all_freshness(self) -> list[MarketDataFreshness]:
        """检查所有活跃省份的数据新鲜度。"""
        sources = await self.source_repo.get_active_sources()
        results = []
        for source in sources:
            freshness = await self.check_data_freshness(source.province)
            results.append(freshness)
        return results

    # --- 手动导入降级 ---

    async def import_market_data_from_records(
        self,
        province: str,
        records: list[dict],
        import_job_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> int:
        """手动导入市场数据（降级方案）。"""
        now = datetime.now(UTC)
        db_records = [
            {
                "trading_date": r["trading_date"],
                "period": r["period"],
                "province": province,
                "clearing_price": Decimal(str(r["clearing_price"])),
                "source": "manual_import",
                "fetched_at": now,
                "import_job_id": import_job_id,
            }
            for r in records
        ]
        count = await self.price_repo.bulk_upsert(db_records)

        if user_id:
            await self.audit_service.log_action(
                user_id=user_id,
                action="import_market_data",
                resource_type="market_clearing_price",
                resource_id=import_job_id or user_id,
                changes_after={
                    "province": province,
                    "records_count": count,
                    "source": "manual_import",
                },
            )

        logger.info(
            "market_data_imported",
            province=province,
            records_count=count,
        )
        return count

    # --- 数据源 CRUD ---

    async def create_source(
        self,
        province: str,
        source_name: str,
        api_endpoint: str | None = None,
        api_key: str | None = None,
        api_auth_type: str = "api_key",
        fetch_schedule: str = "0 7,12,17 * * *",
        is_active: bool = True,
        cache_ttl_seconds: int = 3600,
        user_id: UUID | None = None,
    ) -> MarketDataSource:
        existing = await self.source_repo.get_by_province(province)
        if existing:
            raise BusinessError(
                code="SOURCE_EXISTS",
                message=f"省份 {province} 的数据源已存在",
            )

        source = MarketDataSource(
            province=province,
            source_name=source_name,
            api_endpoint=api_endpoint,
            api_key_encrypted=_encrypt_api_key(api_key) if api_key else None,
            api_auth_type=api_auth_type,
            fetch_schedule=fetch_schedule,
            is_active=is_active,
            cache_ttl_seconds=cache_ttl_seconds,
        )
        created = await self.source_repo.create(source)

        if user_id:
            await self.audit_service.log_action(
                user_id=user_id,
                action="create_market_data_source",
                resource_type="market_data_source",
                resource_id=created.id,
                changes_after={"province": province, "source_name": source_name},
            )
        return created

    async def update_source(
        self,
        source_id: UUID,
        update_data: dict,
        user_id: UUID | None = None,
    ) -> MarketDataSource:
        source = await self.source_repo.get_by_id(source_id)
        if not source:
            raise BusinessError(
                code="SOURCE_NOT_FOUND",
                message="数据源不存在",
                status_code=404,
            )

        before = {"province": source.province}

        if "api_key" in update_data:
            api_key = update_data.pop("api_key")
            if api_key:
                source.api_key_encrypted = _encrypt_api_key(api_key)
            else:
                source.api_key_encrypted = None

        for key, value in update_data.items():
            if value is not None and hasattr(source, key):
                setattr(source, key, value)

        await self.source_repo.session.flush()
        await self.source_repo.session.refresh(source)

        if user_id:
            await self.audit_service.log_action(
                user_id=user_id,
                action="update_market_data_source",
                resource_type="market_data_source",
                resource_id=source_id,
                changes_before=before,
                changes_after=update_data,
            )
        return source

    async def delete_source(
        self,
        source_id: UUID,
        user_id: UUID | None = None,
    ) -> None:
        source = await self.source_repo.get_by_id(source_id)
        if not source:
            raise BusinessError(
                code="SOURCE_NOT_FOUND",
                message="数据源不存在",
                status_code=404,
            )

        if user_id:
            await self.audit_service.log_action(
                user_id=user_id,
                action="delete_market_data_source",
                resource_type="market_data_source",
                resource_id=source_id,
                changes_before={"province": source.province},
            )

        await self.source_repo.delete(source)

    # --- Redis 缓存 ---

    async def _get_cache(self, province: str, trading_date: date) -> list[dict] | None:
        if not self.redis_client:
            return None
        key = f"{CACHE_PREFIX}:{province}:{trading_date.isoformat()}"
        try:
            data = await self.redis_client.get(key)
            return json.loads(data) if data else None
        except Exception:
            return None

    async def _set_cache(
        self,
        province: str,
        trading_date: date,
        records: list[MarketPriceRecord],
        ttl: int,
    ) -> None:
        record_dicts = [
            {
                "period": r.period,
                "clearing_price": str(r.clearing_price),
                "source": "api",
                "fetched_at": datetime.now(UTC).isoformat(),
            }
            for r in records
        ]
        await self._set_cache_raw(province, trading_date, record_dicts, ttl)

    async def _set_cache_raw(
        self,
        province: str,
        trading_date: date,
        records: list[dict],
        ttl: int,
    ) -> None:
        if not self.redis_client:
            return
        key = f"{CACHE_PREFIX}:{province}:{trading_date.isoformat()}"
        try:
            await self.redis_client.setex(key, ttl, json.dumps(records, default=str))
        except Exception as e:
            logger.warning("redis_cache_set_failed", key=key, error=str(e))
