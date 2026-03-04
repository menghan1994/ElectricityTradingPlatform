"""市场数据 API 集成测试 — 使用 dependency_overrides Mock 依赖，
验证 API 层路由/权限守卫/响应格式。
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


_ADMIN_USER_ID = uuid.uuid4()
_TRADER_USER_ID = uuid.uuid4()
_SOURCE_ID = uuid.uuid4()


def _make_admin():
    user = MagicMock()
    user.id = _ADMIN_USER_ID
    user.username = "admin"
    user.role = "admin"
    user.is_active = True
    user.is_locked = False
    return user


def _make_trader():
    user = MagicMock()
    user.id = _TRADER_USER_ID
    user.username = "trader"
    user.role = "trader"
    user.is_active = True
    user.is_locked = False
    return user


def _make_operator():
    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = "operator"
    user.role = "operator"
    user.is_active = True
    user.is_locked = False
    return user


def _make_price(period=1):
    price = MagicMock()
    price.id = uuid.uuid4()
    price.trading_date = date(2026, 3, 1)
    price.period = period
    price.province = "guangdong"
    price.clearing_price = Decimal("350.00")
    price.source = "api"
    price.fetched_at = "2026-03-01T07:00:00+08:00"
    price.import_job_id = None
    price.created_at = "2026-03-01T07:00:00+08:00"
    return price


def _make_source():
    source = MagicMock()
    source.id = _SOURCE_ID
    source.province = "guangdong"
    source.source_name = "广东电力交易中心"
    source.api_endpoint = "https://example.com/api"
    source.api_auth_type = "api_key"
    source.fetch_schedule = "0 7,12,17 * * *"
    source.is_active = True
    source.last_fetch_at = "2026-03-01T07:00:00+08:00"
    source.last_fetch_status = "success"
    source.last_fetch_error = None
    source.cache_ttl_seconds = 3600
    source.created_at = "2026-03-01T00:00:00+08:00"
    source.updated_at = "2026-03-01T07:00:00+08:00"
    return source


@pytest_asyncio.fixture
async def api_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def _override_auth(user):
    from app.core.dependencies import get_current_active_user
    app.dependency_overrides[get_current_active_user] = lambda: user


def _override_service(mock_service):
    from app.api.v1.market_data import _get_market_data_service
    app.dependency_overrides[_get_market_data_service] = lambda: mock_service


class TestListMarketData:
    """GET /api/v1/market-data 测试。"""

    @pytest.mark.asyncio
    async def test_admin_can_list(self, api_client):
        _override_auth(_make_admin())

        mock_service = AsyncMock()
        mock_service.price_repo.list_paginated.return_value = (
            [_make_price(i) for i in range(1, 4)],
            3,
        )
        _override_service(mock_service)

        response = await api_client.get("/api/v1/market-data")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_trader_can_list(self, api_client):
        _override_auth(_make_trader())

        mock_service = AsyncMock()
        mock_service.price_repo.list_paginated.return_value = ([], 0)
        _override_service(mock_service)

        response = await api_client.get("/api/v1/market-data")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_operator_forbidden(self, api_client):
        _override_auth(_make_operator())

        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.get("/api/v1/market-data")
        assert response.status_code == 403


class TestFreshness:
    """GET /api/v1/market-data/freshness 测试。"""

    @pytest.mark.asyncio
    async def test_get_freshness(self, api_client):
        _override_auth(_make_admin())

        from app.schemas.market_data import MarketDataFreshness

        mock_service = AsyncMock()
        mock_service.check_all_freshness.return_value = [
            MarketDataFreshness(
                province="guangdong",
                last_updated="2026-03-01T07:00:00+08:00",
                hours_ago=1.0,
                status="fresh",
            ),
        ]
        _override_service(mock_service)

        response = await api_client.get("/api/v1/market-data/freshness")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "fresh"


class TestTriggerFetch:
    """POST /api/v1/market-data/fetch 测试。"""

    @pytest.mark.asyncio
    async def test_admin_can_trigger(self, api_client):
        _override_auth(_make_admin())

        from app.services.market_data_adapters.base import MarketPriceRecord

        mock_service = AsyncMock()
        mock_service.fetch_market_data.return_value = [
            MarketPriceRecord(
                trading_date=date(2026, 3, 1),
                period=1,
                clearing_price=Decimal("350.00"),
            )
        ]
        _override_service(mock_service)

        response = await api_client.post(
            "/api/v1/market-data/fetch",
            params={"province": "guangdong", "trading_date": "2026-03-01"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["records_count"] == 1

    @pytest.mark.asyncio
    async def test_trader_forbidden(self, api_client):
        _override_auth(_make_trader())

        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.post(
            "/api/v1/market-data/fetch",
            params={"province": "guangdong", "trading_date": "2026-03-01"},
        )
        assert response.status_code == 403


class TestSourceCRUD:
    """数据源 CRUD 端点测试。"""

    @pytest.mark.asyncio
    async def test_list_sources(self, api_client):
        _override_auth(_make_admin())

        mock_service = AsyncMock()
        mock_service.source_repo.list_all_paginated.return_value = (
            [_make_source()],
            1,
        )
        _override_service(mock_service)

        response = await api_client.get("/api/v1/market-data/sources")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_create_source(self, api_client):
        _override_auth(_make_admin())

        mock_service = AsyncMock()
        mock_service.create_source.return_value = _make_source()
        _override_service(mock_service)

        response = await api_client.post(
            "/api/v1/market-data/sources",
            json={
                "province": "guangdong",
                "source_name": "广东电力交易中心",
            },
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_delete_source(self, api_client):
        _override_auth(_make_admin())

        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.delete(f"/api/v1/market-data/sources/{_SOURCE_ID}")
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_trader_cannot_manage_sources(self, api_client):
        _override_auth(_make_trader())

        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.get("/api/v1/market-data/sources")
        assert response.status_code == 403

        response = await api_client.post(
            "/api/v1/market-data/sources",
            json={"province": "test", "source_name": "test"},
        )
        assert response.status_code == 403

        response = await api_client.delete(f"/api/v1/market-data/sources/{_SOURCE_ID}")
        assert response.status_code == 403
