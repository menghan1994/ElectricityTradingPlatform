import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import BusinessError
from app.schemas.market_data import MarketDataFreshness
from app.services.market_data_service import MarketDataService


def _make_source(
    province="guangdong",
    api_endpoint="https://example.com/api",
    api_key_encrypted=None,
    api_auth_type="api_key",
    is_active=True,
    cache_ttl_seconds=3600,
):
    source = MagicMock()
    source.id = uuid.uuid4()
    source.province = province
    source.source_name = "测试数据源"
    source.api_endpoint = api_endpoint
    source.api_key_encrypted = api_key_encrypted
    source.api_auth_type = api_auth_type
    source.is_active = is_active
    source.cache_ttl_seconds = cache_ttl_seconds
    source.fetch_schedule = "0 7,12,17 * * *"
    return source


@pytest.fixture
def mock_price_repo():
    return AsyncMock()


@pytest.fixture
def mock_source_repo():
    return AsyncMock()


@pytest.fixture
def mock_audit_service():
    return AsyncMock()


@pytest.fixture
def mock_redis():
    return AsyncMock()


@pytest.fixture
def service(mock_price_repo, mock_source_repo, mock_audit_service, mock_redis):
    return MarketDataService(
        mock_price_repo,
        mock_source_repo,
        mock_audit_service,
        mock_redis,
    )


class TestFetchMarketData:
    """fetch_market_data 方法测试。"""

    @pytest.mark.asyncio
    async def test_fetch_success(self, service, mock_source_repo, mock_price_repo):
        source = _make_source()
        mock_source_repo.get_by_province.return_value = source
        mock_price_repo.bulk_upsert.return_value = 96

        with patch("app.services.market_data_service.get_adapter") as mock_get_adapter:
            from app.services.market_data_adapters.base import MarketPriceRecord

            mock_adapter = AsyncMock()
            mock_adapter.fetch.return_value = [
                MarketPriceRecord(
                    trading_date=date(2026, 3, 1),
                    period=i,
                    clearing_price=Decimal("350.00"),
                )
                for i in range(1, 97)
            ]
            mock_get_adapter.return_value = mock_adapter

            records = await service.fetch_market_data("guangdong", date(2026, 3, 1))
            assert len(records) == 96
            mock_price_repo.bulk_upsert.assert_called_once()
            mock_source_repo.update_fetch_status.assert_called()

    @pytest.mark.asyncio
    async def test_fetch_source_not_found(self, service, mock_source_repo):
        mock_source_repo.get_by_province.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await service.fetch_market_data("guangdong", date(2026, 3, 1))
        assert exc_info.value.code == "SOURCE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_fetch_no_endpoint(self, service, mock_source_repo):
        source = _make_source(api_endpoint=None)
        mock_source_repo.get_by_province.return_value = source

        with pytest.raises(BusinessError) as exc_info:
            await service.fetch_market_data("guangdong", date(2026, 3, 1))
        assert exc_info.value.code == "SOURCE_NO_ENDPOINT"

    @pytest.mark.asyncio
    async def test_fetch_api_failure_updates_status(
        self, service, mock_source_repo
    ):
        source = _make_source()
        mock_source_repo.get_by_province.return_value = source

        with patch("app.services.market_data_service.get_adapter") as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.fetch.side_effect = RuntimeError("连接超时")
            mock_get_adapter.return_value = mock_adapter

            with pytest.raises(BusinessError) as exc_info:
                await service.fetch_market_data("guangdong", date(2026, 3, 1))
            assert exc_info.value.code == "FETCH_FAILED"
            mock_source_repo.update_fetch_status.assert_called_with(
                source.id, "failed", error_message="连接超时",
            )

    @pytest.mark.asyncio
    async def test_fetch_with_audit(
        self, service, mock_source_repo, mock_price_repo, mock_audit_service
    ):
        source = _make_source()
        mock_source_repo.get_by_province.return_value = source
        mock_price_repo.bulk_upsert.return_value = 96
        user_id = uuid.uuid4()

        with patch("app.services.market_data_service.get_adapter") as mock_get_adapter:
            from app.services.market_data_adapters.base import MarketPriceRecord

            mock_adapter = AsyncMock()
            mock_adapter.fetch.return_value = [
                MarketPriceRecord(
                    trading_date=date(2026, 3, 1),
                    period=1,
                    clearing_price=Decimal("350.00"),
                )
            ]
            mock_get_adapter.return_value = mock_adapter

            await service.fetch_market_data("guangdong", date(2026, 3, 1), user_id=user_id)
            mock_audit_service.log_action.assert_called_once()


class TestCheckDataFreshness:
    """check_data_freshness 方法测试。"""

    @pytest.mark.asyncio
    async def test_no_data_returns_critical(self, service, mock_price_repo):
        mock_price_repo.check_freshness.return_value = None
        result = await service.check_data_freshness("guangdong")
        assert result.status == "critical"
        assert result.last_updated is None

    @pytest.mark.asyncio
    async def test_fresh_data(self, service, mock_price_repo):
        now = datetime.now(UTC)
        mock_price_repo.check_freshness.return_value = now
        result = await service.check_data_freshness("guangdong")
        assert result.status == "fresh"

    @pytest.mark.asyncio
    async def test_stale_data(self, service, mock_price_repo):
        from datetime import timedelta
        stale_time = datetime.now(UTC) - timedelta(hours=6)
        mock_price_repo.check_freshness.return_value = stale_time
        result = await service.check_data_freshness("guangdong")
        assert result.status == "stale"

    @pytest.mark.asyncio
    async def test_expired_data(self, service, mock_price_repo):
        from datetime import timedelta
        expired_time = datetime.now(UTC) - timedelta(hours=18)
        mock_price_repo.check_freshness.return_value = expired_time
        result = await service.check_data_freshness("guangdong")
        assert result.status == "expired"

    @pytest.mark.asyncio
    async def test_critical_data(self, service, mock_price_repo):
        from datetime import timedelta
        critical_time = datetime.now(UTC) - timedelta(hours=30)
        mock_price_repo.check_freshness.return_value = critical_time
        result = await service.check_data_freshness("guangdong")
        assert result.status == "critical"


class TestSourceCRUD:
    """数据源 CRUD 操作测试。"""

    @pytest.mark.asyncio
    async def test_create_source(self, service, mock_source_repo):
        mock_source_repo.get_by_province.return_value = None
        mock_source_repo.create.return_value = _make_source()

        result = await service.create_source(
            province="guangdong",
            source_name="广东电力交易中心",
        )
        assert result.province == "guangdong"
        mock_source_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_duplicate_rejected(self, service, mock_source_repo):
        mock_source_repo.get_by_province.return_value = _make_source()

        with pytest.raises(BusinessError) as exc_info:
            await service.create_source(
                province="guangdong",
                source_name="广东电力交易中心",
            )
        assert exc_info.value.code == "SOURCE_EXISTS"

    @pytest.mark.asyncio
    async def test_delete_source_not_found(self, service, mock_source_repo):
        mock_source_repo.get_by_id.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await service.delete_source(uuid.uuid4())
        assert exc_info.value.code == "SOURCE_NOT_FOUND"


class TestImportMarketData:
    """手动导入市场数据测试。"""

    @pytest.mark.asyncio
    async def test_import_records(self, service, mock_price_repo):
        mock_price_repo.bulk_upsert.return_value = 96
        records = [
            {"trading_date": date(2026, 3, 1), "period": i, "clearing_price": "350.00"}
            for i in range(1, 97)
        ]
        count = await service.import_market_data_from_records("guangdong", records)
        assert count == 96
        mock_price_repo.bulk_upsert.assert_called_once()
