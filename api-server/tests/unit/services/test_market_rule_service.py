"""MarketRuleService 单元测试 — Mock Repository 依赖，验证业务逻辑。"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import BusinessError
from app.models.market_rule import ProvinceMarketRule
from app.schemas.market_rule import MarketRuleCreate
from app.services.market_rule_service import MarketRuleService


@pytest.fixture
def mock_market_rule_repo():
    repo = AsyncMock()
    repo.session = AsyncMock()
    return repo


@pytest.fixture
def mock_audit_service():
    return AsyncMock()


@pytest.fixture
def service(mock_market_rule_repo, mock_audit_service):
    return MarketRuleService(mock_market_rule_repo, mock_audit_service)


def _make_admin():
    admin = MagicMock()
    admin.id = uuid4()
    admin.username = "admin"
    admin.role = "admin"
    return admin


def _make_rule(**kwargs):
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
    }
    defaults.update(kwargs)
    rule = MagicMock(spec=ProvinceMarketRule)
    for k, v in defaults.items():
        setattr(rule, k, v)
    return rule


def _valid_create_data(**overrides):
    defaults = {
        "price_cap_upper": Decimal("1500.00"),
        "price_cap_lower": Decimal("0.00"),
        "settlement_method": "spot",
        "deviation_formula_type": "stepped",
        "deviation_formula_params": {
            "exemption_ratio": 0.03,
            "steps": [{"lower": 0.03, "upper": 0.05, "rate": 0.5}],
        },
    }
    defaults.update(overrides)
    return MarketRuleCreate(**defaults)


class TestCreateOrUpdateMarketRule:
    @pytest.mark.asyncio
    async def test_create_new_rule(self, service, mock_market_rule_repo, mock_audit_service):
        admin = _make_admin()
        mock_market_rule_repo.get_by_province_for_update.return_value = None
        mock_market_rule_repo.create.side_effect = lambda r: r

        data = _valid_create_data()
        result = await service.create_or_update_market_rule(
            "guangdong", data, admin, "192.168.1.1",
        )

        assert result.province == "guangdong"
        mock_audit_service.log_action.assert_called_once()
        call_kwargs = mock_audit_service.log_action.call_args.kwargs
        assert call_kwargs["action"] == "create_market_rule"

    @pytest.mark.asyncio
    async def test_update_existing_rule(self, service, mock_market_rule_repo, mock_audit_service):
        admin = _make_admin()
        existing = _make_rule()
        mock_market_rule_repo.get_by_province_for_update.return_value = existing

        data = _valid_create_data(price_cap_upper=Decimal("2000.00"))
        result = await service.create_or_update_market_rule(
            "guangdong", data, admin, "192.168.1.1",
        )

        assert result is existing
        mock_audit_service.log_action.assert_called_once()
        call_kwargs = mock_audit_service.log_action.call_args.kwargs
        assert call_kwargs["action"] == "update_market_rule"
        assert "price_cap_upper" in call_kwargs["changes_after"]

    @pytest.mark.asyncio
    async def test_invalid_deviation_params_rejected(self, service, mock_market_rule_repo):
        admin = _make_admin()
        mock_market_rule_repo.get_by_province_for_update.return_value = None

        data = _valid_create_data(
            deviation_formula_type="stepped",
            deviation_formula_params={"invalid_key": "bad"},
        )

        with pytest.raises(BusinessError) as exc_info:
            await service.create_or_update_market_rule("guangdong", data, admin)

        assert exc_info.value.code == "INVALID_DEVIATION_PARAMS"
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_reactivates_inactive_rule(self, service, mock_market_rule_repo, mock_audit_service):
        admin = _make_admin()
        existing = _make_rule(is_active=False)
        mock_market_rule_repo.get_by_province_for_update.return_value = existing

        data = _valid_create_data()
        await service.create_or_update_market_rule("guangdong", data, admin)

        mock_audit_service.log_action.assert_called_once()
        call_kwargs = mock_audit_service.log_action.call_args.kwargs
        assert call_kwargs["changes_after"]["is_active"] is True


class TestGetMarketRule:
    @pytest.mark.asyncio
    async def test_get_existing_rule(self, service, mock_market_rule_repo):
        rule = _make_rule()
        mock_market_rule_repo.get_by_province.return_value = rule

        result = await service.get_market_rule("guangdong")
        assert result is rule

    @pytest.mark.asyncio
    async def test_get_nonexistent_rule(self, service, mock_market_rule_repo):
        mock_market_rule_repo.get_by_province.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await service.get_market_rule("guangdong")

        assert exc_info.value.code == "MARKET_RULE_NOT_FOUND"
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_inactive_rule_raises_not_found(self, service, mock_market_rule_repo):
        rule = _make_rule(is_active=False)
        mock_market_rule_repo.get_by_province.return_value = rule

        with pytest.raises(BusinessError) as exc_info:
            await service.get_market_rule("guangdong")

        assert exc_info.value.code == "MARKET_RULE_NOT_FOUND"
        assert exc_info.value.status_code == 404


class TestDeleteMarketRule:
    @pytest.mark.asyncio
    async def test_soft_delete_success(self, service, mock_market_rule_repo, mock_audit_service):
        admin = _make_admin()
        rule = _make_rule()
        mock_market_rule_repo.get_by_province_for_update.return_value = rule

        await service.delete_market_rule("guangdong", admin, "192.168.1.1")

        mock_audit_service.log_action.assert_called_once()
        call_kwargs = mock_audit_service.log_action.call_args.kwargs
        assert call_kwargs["action"] == "delete_market_rule"

    @pytest.mark.asyncio
    async def test_delete_nonexistent_raises(self, service, mock_market_rule_repo):
        admin = _make_admin()
        mock_market_rule_repo.get_by_province_for_update.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await service.delete_market_rule("guangdong", admin)

        assert exc_info.value.code == "MARKET_RULE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_delete_already_inactive_raises(self, service, mock_market_rule_repo):
        admin = _make_admin()
        rule = _make_rule(is_active=False)
        mock_market_rule_repo.get_by_province_for_update.return_value = rule

        with pytest.raises(BusinessError) as exc_info:
            await service.delete_market_rule("guangdong", admin)

        assert exc_info.value.code == "MARKET_RULE_NOT_FOUND"


class TestCreateIntegrityError:
    @pytest.mark.asyncio
    async def test_integrity_error_returns_409(self, service, mock_market_rule_repo):
        from sqlalchemy.exc import IntegrityError

        admin = _make_admin()
        mock_market_rule_repo.get_by_province_for_update.return_value = None
        mock_market_rule_repo.create.side_effect = IntegrityError(
            "duplicate", params=None, orig=Exception("unique violation"),
        )

        data = _valid_create_data()
        with pytest.raises(BusinessError) as exc_info:
            await service.create_or_update_market_rule("guangdong", data, admin)

        assert exc_info.value.code == "PROVINCE_RULE_ALREADY_EXISTS"
        assert exc_info.value.status_code == 409


class TestListMarketRules:
    @pytest.mark.asyncio
    async def test_list_returns_active_rules(self, service, mock_market_rule_repo):
        rules = [_make_rule(province="guangdong"), _make_rule(province="gansu")]
        mock_market_rule_repo.list_all_active.return_value = rules

        result = await service.list_market_rules()
        assert len(result) == 2
