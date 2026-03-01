"""MarketRule Schema 单元测试 — 校验 Pydantic 模型的验证逻辑。"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.market_rule import (
    BandwidthParams,
    MarketRuleCreate,
    ProportionalParams,
    SteppedParams,
    SteppedStep,
)


class TestMarketRuleCreate:
    def test_valid_create(self):
        data = MarketRuleCreate(
            price_cap_upper=Decimal("1500.00"),
            price_cap_lower=Decimal("0.00"),
            settlement_method="spot",
            deviation_formula_type="stepped",
            deviation_formula_params={"exemption_ratio": 0.03, "steps": []},
        )
        assert data.price_cap_upper == Decimal("1500.00")
        assert data.settlement_method == "spot"

    def test_price_cap_upper_must_exceed_lower(self):
        with pytest.raises(ValidationError, match="最高限价必须大于最低限价"):
            MarketRuleCreate(
                price_cap_upper=Decimal("100.00"),
                price_cap_lower=Decimal("200.00"),
                settlement_method="spot",
                deviation_formula_type="stepped",
                deviation_formula_params={},
            )

    def test_price_cap_equal_rejected(self):
        with pytest.raises(ValidationError, match="最高限价必须大于最低限价"):
            MarketRuleCreate(
                price_cap_upper=Decimal("100.00"),
                price_cap_lower=Decimal("100.00"),
                settlement_method="spot",
                deviation_formula_type="stepped",
                deviation_formula_params={},
            )

    def test_invalid_settlement_method(self):
        with pytest.raises(ValidationError):
            MarketRuleCreate(
                price_cap_upper=Decimal("1500.00"),
                price_cap_lower=Decimal("0.00"),
                settlement_method="invalid",
                deviation_formula_type="stepped",
                deviation_formula_params={},
            )

    def test_invalid_deviation_formula_type(self):
        with pytest.raises(ValidationError):
            MarketRuleCreate(
                price_cap_upper=Decimal("1500.00"),
                price_cap_lower=Decimal("0.00"),
                settlement_method="spot",
                deviation_formula_type="invalid",
                deviation_formula_params={},
            )

    def test_price_cap_upper_must_be_positive(self):
        with pytest.raises(ValidationError):
            MarketRuleCreate(
                price_cap_upper=Decimal("0.00"),
                price_cap_lower=Decimal("0.00"),
                settlement_method="spot",
                deviation_formula_type="stepped",
                deviation_formula_params={},
            )

    def test_price_cap_lower_allows_zero(self):
        data = MarketRuleCreate(
            price_cap_upper=Decimal("100.00"),
            price_cap_lower=Decimal("0.00"),
            settlement_method="spot",
            deviation_formula_type="stepped",
            deviation_formula_params={},
        )
        assert data.price_cap_lower == Decimal("0.00")



class TestSteppedStepValidation:
    def test_valid_step(self):
        step = SteppedStep(lower=0.03, upper=0.05, rate=0.5)
        assert step.lower == 0.03
        assert step.upper == 0.05

    def test_lower_must_be_less_than_upper(self):
        with pytest.raises(ValidationError, match="阶梯下限必须小于上限"):
            SteppedStep(lower=0.05, upper=0.03, rate=0.5)

    def test_equal_lower_upper_rejected(self):
        with pytest.raises(ValidationError, match="阶梯下限必须小于上限"):
            SteppedStep(lower=0.05, upper=0.05, rate=0.5)


class TestSteppedParams:
    def test_valid_stepped(self):
        params = SteppedParams(
            exemption_ratio=0.03,
            steps=[SteppedStep(lower=0.03, upper=0.05, rate=0.5)],
        )
        assert params.exemption_ratio == 0.03
        assert len(params.steps) == 1

    def test_steps_required(self):
        with pytest.raises(ValidationError):
            SteppedParams(exemption_ratio=0.03, steps=[])

    def test_exemption_ratio_range(self):
        with pytest.raises(ValidationError):
            SteppedParams(exemption_ratio=1.0, steps=[SteppedStep(lower=0, upper=0.5, rate=1)])


class TestProportionalParams:
    def test_valid_proportional(self):
        params = ProportionalParams(exemption_ratio=0.05, base_rate=1.0)
        assert params.base_rate == 1.0

    def test_base_rate_positive(self):
        with pytest.raises(ValidationError):
            ProportionalParams(exemption_ratio=0.05, base_rate=0)


class TestBandwidthParams:
    def test_valid_bandwidth(self):
        params = BandwidthParams(bandwidth_percent=0.02, penalty_rate=0.8)
        assert params.bandwidth_percent == 0.02

    def test_bandwidth_percent_range(self):
        with pytest.raises(ValidationError):
            BandwidthParams(bandwidth_percent=1.0, penalty_rate=0.8)
