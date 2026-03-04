from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.market_data_adapters.base import MarketPriceRecord
from app.services.market_data_adapters.generic import GenericMarketDataAdapter


@pytest.fixture
def adapter():
    return GenericMarketDataAdapter(
        api_endpoint="https://example.com/api/prices",
        api_key="test-key-123",
        api_auth_type="api_key",
    )


@pytest.fixture
def adapter_bearer():
    return GenericMarketDataAdapter(
        api_endpoint="https://example.com/api/prices",
        api_key="bearer-token-456",
        api_auth_type="bearer",
    )


@pytest.fixture
def adapter_no_auth():
    return GenericMarketDataAdapter(
        api_endpoint="https://example.com/api/prices",
        api_auth_type="none",
    )


class TestGenericAdapter:
    """GenericMarketDataAdapter 单元测试。"""

    def test_build_headers_api_key(self, adapter):
        headers = adapter._build_headers()
        assert headers["X-API-Key"] == "test-key-123"
        assert "Authorization" not in headers

    def test_build_headers_bearer(self, adapter_bearer):
        headers = adapter_bearer._build_headers()
        assert headers["Authorization"] == "Bearer bearer-token-456"
        assert "X-API-Key" not in headers

    def test_build_headers_no_auth(self, adapter_no_auth):
        headers = adapter_no_auth._build_headers()
        assert "X-API-Key" not in headers
        assert "Authorization" not in headers

    def test_parse_response(self, adapter):
        data = {
            "data": [
                {"period": 1, "clearing_price": 350.00},
                {"period": 2, "clearing_price": 345.50},
            ]
        }
        records = adapter._parse_response(date(2026, 3, 1), data)
        assert len(records) == 2
        assert records[0].period == 1
        assert records[0].clearing_price == Decimal("350.0")
        assert records[1].period == 2

    def test_parse_response_empty(self, adapter):
        data = {"data": []}
        records = adapter._parse_response(date(2026, 3, 1), data)
        assert len(records) == 0

    @pytest.mark.asyncio
    async def test_fetch_success(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": [{"period": i, "clearing_price": 350.0} for i in range(1, 97)]
        }

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            records = await adapter.fetch(date(2026, 3, 1))
            assert len(records) == 96

    @pytest.mark.asyncio
    async def test_fetch_retry_on_failure(self, adapter):
        """验证重试逻辑：前两次失败，第三次成功。"""
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.raise_for_status = MagicMock()
        mock_success_response.json.return_value = {
            "data": [{"period": 1, "clearing_price": 350.0}]
        }

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("连接失败")
            return mock_success_response

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = mock_get
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            records = await adapter.fetch(date(2026, 3, 1))
            assert len(records) == 1
            assert call_count == 3

    @pytest.mark.asyncio
    async def test_fetch_all_retries_exhausted(self, adapter):
        """验证所有重试耗尽后抛出 RuntimeError。"""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("连接失败")
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(RuntimeError, match="市场数据获取失败"):
                await adapter.fetch(date(2026, 3, 1))

    @pytest.mark.asyncio
    async def test_health_check_success(self, adapter):
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.head.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await adapter.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, adapter):
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.head.side_effect = httpx.ConnectError("连接失败")
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await adapter.health_check()
            assert result is False
