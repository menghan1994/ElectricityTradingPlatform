from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas.market_data import (
    MarketClearingPriceListResponse,
    MarketClearingPriceRead,
    MarketDataFetchResult,
    MarketDataFreshness,
    MarketDataSourceCreate,
    MarketDataSourceRead,
    MarketDataSourceUpdate,
)


class TestMarketClearingPriceRead:
    """MarketClearingPriceRead schema 转换测试。"""

    def test_from_attributes(self):
        class FakePrice:
            id = "550e8400-e29b-41d4-a716-446655440000"
            trading_date = "2026-03-01"
            period = 1
            province = "guangdong"
            clearing_price = Decimal("350.00")
            source = "api"
            fetched_at = "2026-03-01T07:00:00+08:00"
            import_job_id = None
            created_at = "2026-03-01T07:00:00+08:00"

        result = MarketClearingPriceRead.model_validate(FakePrice(), from_attributes=True)
        assert result.period == 1
        assert result.province == "guangdong"
        assert result.source == "api"
        assert result.import_job_id is None
        assert isinstance(result.id, UUID)

    def test_invalid_source_rejected(self):
        with pytest.raises(ValidationError):
            MarketClearingPriceRead(
                id="550e8400-e29b-41d4-a716-446655440000",
                trading_date="2026-03-01",
                period=1,
                province="guangdong",
                clearing_price=Decimal("350.00"),
                source="invalid_source",
                fetched_at="2026-03-01T07:00:00+08:00",
                import_job_id=None,
                created_at="2026-03-01T07:00:00+08:00",
            )


class TestMarketDataSourceCreate:
    """MarketDataSourceCreate schema 测试。"""

    def test_valid_create(self):
        result = MarketDataSourceCreate(
            province="guangdong",
            source_name="广东电力交易中心",
        )
        assert result.province == "guangdong"
        assert result.api_auth_type == "api_key"
        assert result.cache_ttl_seconds == 3600

    def test_empty_province_rejected(self):
        with pytest.raises(ValidationError):
            MarketDataSourceCreate(province="  ", source_name="test")

    def test_invalid_cache_ttl_rejected(self):
        with pytest.raises(ValidationError):
            MarketDataSourceCreate(
                province="guangdong",
                source_name="test",
                cache_ttl_seconds=0,
            )

    def test_negative_cache_ttl_rejected(self):
        with pytest.raises(ValidationError):
            MarketDataSourceCreate(
                province="guangdong",
                source_name="test",
                cache_ttl_seconds=-1,
            )


class TestMarketDataSourceUpdate:
    """MarketDataSourceUpdate schema 测试。"""

    def test_partial_update(self):
        result = MarketDataSourceUpdate(source_name="新名称")
        assert result.source_name == "新名称"
        assert result.api_endpoint is None
        assert result.is_active is None

    def test_invalid_cache_ttl(self):
        with pytest.raises(ValidationError):
            MarketDataSourceUpdate(cache_ttl_seconds=0)


class TestMarketDataSourceRead:
    """MarketDataSourceRead schema 测试。"""

    def test_from_attributes(self):
        class FakeSource:
            id = "550e8400-e29b-41d4-a716-446655440000"
            province = "guangdong"
            source_name = "广东电力交易中心"
            api_endpoint = "https://example.com/api"
            api_auth_type = "api_key"
            fetch_schedule = "0 7,12,17 * * *"
            is_active = True
            last_fetch_at = "2026-03-01T07:00:00+08:00"
            last_fetch_status = "success"
            last_fetch_error = None
            cache_ttl_seconds = 3600
            created_at = "2026-03-01T00:00:00+08:00"
            updated_at = "2026-03-01T07:00:00+08:00"

        result = MarketDataSourceRead.model_validate(FakeSource(), from_attributes=True)
        assert result.province == "guangdong"
        assert result.is_active is True
        assert result.last_fetch_status == "success"

    def test_api_key_not_exposed(self):
        """验证 Read schema 不包含 api_key 字段。"""
        fields = MarketDataSourceRead.model_fields
        assert "api_key" not in fields
        assert "api_key_encrypted" not in fields


class TestMarketDataFreshness:
    """MarketDataFreshness schema 测试。"""

    def test_fresh_status(self):
        result = MarketDataFreshness(
            province="guangdong",
            last_updated="2026-03-01T07:00:00+08:00",
            hours_ago=0.5,
            status="fresh",
        )
        assert result.status == "fresh"
        assert result.hours_ago == 0.5

    def test_critical_no_data(self):
        result = MarketDataFreshness(
            province="guangdong",
            last_updated=None,
            hours_ago=None,
            status="critical",
        )
        assert result.last_updated is None
        assert result.status == "critical"

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            MarketDataFreshness(
                province="guangdong",
                last_updated=None,
                hours_ago=None,
                status="unknown",
            )


class TestMarketDataFetchResult:
    """MarketDataFetchResult schema 测试。"""

    def test_success_result(self):
        result = MarketDataFetchResult(
            province="guangdong",
            trading_date="2026-03-01",
            records_count=96,
            status="success",
        )
        assert result.records_count == 96
        assert result.error_message is None

    def test_failed_result(self):
        result = MarketDataFetchResult(
            province="guangdong",
            trading_date="2026-03-01",
            records_count=0,
            status="failed",
            error_message="连接超时",
        )
        assert result.error_message == "连接超时"


class TestMarketClearingPriceListResponse:
    """MarketClearingPriceListResponse 测试。"""

    def test_construction(self):
        response = MarketClearingPriceListResponse(
            items=[],
            total=0,
            page=1,
            page_size=96,
        )
        assert response.total == 0
        assert response.page_size == 96
