"""市场规则 API 集成测试 — 使用 dependency_overrides Mock 依赖，
验证 API 层路由/权限守卫/响应格式。"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import BusinessError
from app.main import app
from app.models.market_rule import ProvinceMarketRule
from app.models.user import User
from app.schemas.user import RoleType


def _make_user_obj(role: "RoleType" = "admin") -> MagicMock:
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.username = "admin"
    user.role = role
    user.is_active = True
    user.is_locked = False
    return user


def _make_rule_obj(**kwargs) -> MagicMock:
    defaults = {
        "id": uuid4(),
        "province": "guangdong",
        "price_cap_upper": Decimal("1500.00"),
        "price_cap_lower": Decimal("0.00"),
        "settlement_method": "spot",
        "deviation_formula_type": "stepped",
        "deviation_formula_params": {
            "exemption_ratio": 0.03,
            "steps": [{"lower": 0.03, "upper": 0.05, "rate": 0.5}],
        },
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    rule = MagicMock(spec=ProvinceMarketRule)
    for k, v in defaults.items():
        setattr(rule, k, v)
    return rule


def _create_mock_service(rules=None):
    from app.services.market_rule_service import MarketRuleService

    service = AsyncMock(spec=MarketRuleService)

    if rules is None:
        rules = [_make_rule_obj()]

    service.list_market_rules.return_value = rules
    service.get_market_rule.return_value = rules[0] if rules else None
    service.create_or_update_market_rule.return_value = rules[0] if rules else _make_rule_obj()
    service.delete_market_rule.return_value = None

    return service


@pytest_asyncio.fixture
async def api_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def _setup_admin_overrides(mock_service):
    from app.api.v1.market_rules import _get_market_rule_service
    from app.core.dependencies import get_current_active_user, require_roles
    from app.core.data_access import require_write_permission

    admin_user = _make_user_obj("admin")

    app.dependency_overrides[_get_market_rule_service] = lambda: mock_service
    app.dependency_overrides[get_current_active_user] = lambda: admin_user

    def _fake_require_roles(roles):
        async def _inner():
            return admin_user
        return _inner

    app.dependency_overrides[require_roles] = _fake_require_roles
    app.dependency_overrides[require_write_permission] = lambda: admin_user

    return admin_user


def _setup_non_admin_overrides(mock_service):
    from app.api.v1.market_rules import _get_market_rule_service
    from app.core.dependencies import get_current_active_user

    trader_user = _make_user_obj("trader")

    app.dependency_overrides[_get_market_rule_service] = lambda: mock_service
    app.dependency_overrides[get_current_active_user] = lambda: trader_user


class TestListMarketRules:
    @pytest.mark.asyncio
    async def test_admin_list_rules(self, api_client):
        mock_service = _create_mock_service()
        _setup_admin_overrides(mock_service)

        response = await api_client.get(
            "/api/v1/market-rules",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

    @pytest.mark.asyncio
    async def test_non_admin_forbidden(self, api_client):
        mock_service = _create_mock_service()
        _setup_non_admin_overrides(mock_service)

        response = await api_client.get(
            "/api/v1/market-rules",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403


class TestGetMarketRule:
    @pytest.mark.asyncio
    async def test_get_existing_rule(self, api_client):
        mock_service = _create_mock_service()
        _setup_admin_overrides(mock_service)

        response = await api_client.get(
            "/api/v1/market-rules/guangdong",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["province"] == "guangdong"

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_404(self, api_client):
        mock_service = _create_mock_service()
        mock_service.get_market_rule.side_effect = BusinessError(
            code="MARKET_RULE_NOT_FOUND", message="not found", status_code=404,
        )
        _setup_admin_overrides(mock_service)

        response = await api_client.get(
            "/api/v1/market-rules/gansu",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_province_returns_422(self, api_client):
        mock_service = _create_mock_service()
        _setup_admin_overrides(mock_service)

        response = await api_client.get(
            "/api/v1/market-rules/invalid_province",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 422


class TestUpsertMarketRule:
    @pytest.mark.asyncio
    async def test_create_rule_success(self, api_client):
        mock_service = _create_mock_service()
        _setup_admin_overrides(mock_service)

        response = await api_client.put(
            "/api/v1/market-rules/guangdong",
            json={
                "price_cap_upper": 1500.00,
                "price_cap_lower": 0.00,
                "settlement_method": "spot",
                "deviation_formula_type": "stepped",
                "deviation_formula_params": {
                    "exemption_ratio": 0.03,
                    "steps": [{"lower": 0.03, "upper": 0.05, "rate": 0.5}],
                },
            },
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_price_cap_invalid_returns_422(self, api_client):
        mock_service = _create_mock_service()
        _setup_admin_overrides(mock_service)

        response = await api_client.put(
            "/api/v1/market-rules/guangdong",
            json={
                "price_cap_upper": 100.00,
                "price_cap_lower": 200.00,
                "settlement_method": "spot",
                "deviation_formula_type": "stepped",
                "deviation_formula_params": {},
            },
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 422


class TestDeleteMarketRule:
    @pytest.mark.asyncio
    async def test_delete_returns_204(self, api_client):
        mock_service = _create_mock_service()
        _setup_admin_overrides(mock_service)

        response = await api_client.delete(
            "/api/v1/market-rules/guangdong",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_non_admin_delete_forbidden(self, api_client):
        mock_service = _create_mock_service()
        _setup_non_admin_overrides(mock_service)

        response = await api_client.delete(
            "/api/v1/market-rules/guangdong",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403
