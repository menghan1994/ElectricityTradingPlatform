from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.prediction_adapters.generic import GenericPredictionAdapter


@pytest.fixture
def adapter():
    return GenericPredictionAdapter(
        api_endpoint="https://api.example.com/predict",
        api_key="test-key",
        api_auth_type="api_key",
        timeout_seconds=10,
    )


class TestGenericPredictionAdapter:
    """GenericPredictionAdapter 单元测试。"""

    @pytest.mark.asyncio
    async def test_fetch_predictions_success(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = [
            {
                "period": 1,
                "predicted_power_kw": "1500.00",
                "confidence_upper_kw": "1650.00",
                "confidence_lower_kw": "1350.00",
            },
            {
                "period": 2,
                "predicted_power_kw": "1480.00",
                "confidence_upper_kw": "1620.00",
                "confidence_lower_kw": "1340.00",
            },
        ]

        with patch("app.services.prediction_adapters.generic.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            records = await adapter.fetch_predictions("station-1", date(2026, 3, 1))
            assert len(records) == 2
            assert records[0].period == 1
            assert records[0].predicted_power_kw == Decimal("1500.00")
            assert records[0].confidence_upper_kw == Decimal("1650.00")
            assert records[0].confidence_lower_kw == Decimal("1350.00")

    @pytest.mark.asyncio
    async def test_fetch_predictions_with_data_wrapper(self, adapter):
        """测试 API 返回 {"data": [...]} 格式。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "period": 1,
                    "predicted_power_kw": "1500.00",
                    "confidence_upper_kw": "1650.00",
                    "confidence_lower_kw": "1350.00",
                },
            ]
        }

        with patch("app.services.prediction_adapters.generic.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            records = await adapter.fetch_predictions("station-1", date(2026, 3, 1))
            assert len(records) == 1

    @pytest.mark.asyncio
    async def test_fetch_predictions_retry_on_failure(self, adapter):
        """测试重试逻辑：第一次失败，第二次成功。"""
        import httpx

        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.raise_for_status = MagicMock()
        mock_success_response.json.return_value = [
            {
                "period": 1,
                "predicted_power_kw": "1500.00",
                "confidence_upper_kw": "1650.00",
                "confidence_lower_kw": "1350.00",
            },
        ]

        with patch("app.services.prediction_adapters.generic.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.side_effect = [
                httpx.ConnectError("连接失败"),
                mock_success_response,
            ]
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.services.prediction_adapters.generic.asyncio.sleep", new_callable=AsyncMock):
                records = await adapter.fetch_predictions("station-1", date(2026, 3, 1))
                assert len(records) == 1

    @pytest.mark.asyncio
    async def test_fetch_predictions_all_retries_fail(self, adapter):
        """测试所有重试都失败后抛出异常。"""
        import httpx

        with patch("app.services.prediction_adapters.generic.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("连接失败")
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.services.prediction_adapters.generic.asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(RuntimeError, match="功率预测获取失败"):
                    await adapter.fetch_predictions("station-1", date(2026, 3, 1))

    @pytest.mark.asyncio
    async def test_health_check_success(self, adapter):
        with patch("app.services.prediction_adapters.generic.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.head.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await adapter.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_server_error(self, adapter):
        with patch("app.services.prediction_adapters.generic.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_client.head.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await adapter.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_connection_error(self, adapter):
        import httpx

        with patch("app.services.prediction_adapters.generic.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.head.side_effect = httpx.ConnectError("连接失败")
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await adapter.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_timeout(self, adapter):
        """测试 asyncio.TimeoutError 路径。"""
        import asyncio

        with patch("app.services.prediction_adapters.generic.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.head.side_effect = asyncio.TimeoutError()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await adapter.health_check()
            assert result is False

    def test_build_headers_api_key(self, adapter):
        headers = adapter._build_headers()
        assert headers["X-API-Key"] == "test-key"
        assert "Authorization" not in headers

    def test_build_headers_bearer(self):
        adapter = GenericPredictionAdapter(
            api_endpoint="https://api.example.com",
            api_key="bearer-token",
            api_auth_type="bearer",
        )
        headers = adapter._build_headers()
        assert headers["Authorization"] == "Bearer bearer-token"
        assert "X-API-Key" not in headers

    def test_build_headers_no_auth(self):
        adapter = GenericPredictionAdapter(
            api_endpoint="https://api.example.com",
            api_auth_type="none",
        )
        headers = adapter._build_headers()
        assert "Authorization" not in headers
        assert "X-API-Key" not in headers

    def test_get_adapter_info(self, adapter):
        info = adapter.get_adapter_info()
        assert info["name"] == "GenericPredictionAdapter"
        assert "wind" in info["supported_types"]
