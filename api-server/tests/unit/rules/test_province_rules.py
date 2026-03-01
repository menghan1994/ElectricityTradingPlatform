"""省份规则引擎单元测试 — 测试注册机制和计算正确性。"""

from decimal import Decimal

import pytest

from rules.registry import registry, register_province
from rules.guangdong import GuangdongRule
from rules.gansu import GansuRule
from rules.loader import load_province_config, load_all_province_plugins


class TestRegisterProvince:
    def test_guangdong_registered(self):
        rule = registry.get("guangdong")
        assert rule is not None
        assert isinstance(rule, GuangdongRule)

    def test_gansu_registered(self):
        rule = registry.get("gansu")
        assert rule is not None
        assert isinstance(rule, GansuRule)

    def test_unregistered_province_returns_none(self):
        rule = registry.get("nonexistent")
        assert rule is None

    def test_list_names_includes_provinces(self):
        names = registry.list_names()
        assert "guangdong" in names
        assert "gansu" in names

    def test_register_province_decorator(self):
        @register_province("test_province")
        class TestRule:
            pass

        assert registry.get("test_province") is not None
        # 清理
        registry._rules.pop("test_province", None)


class TestGuangdongDeviationCost:
    """广东省阶梯式偏差考核测试。"""

    def setup_method(self):
        self.rule = GuangdongRule()
        self.params = {
            "exemption_ratio": 0.03,
            "steps": [
                {"lower": 0.03, "upper": 0.05, "rate": 0.5},
                {"lower": 0.05, "upper": 1.0, "rate": 1.0},
            ],
        }

    def test_zero_deviation(self):
        """偏差为 0 时不考核。"""
        cost = self.rule.calculate_deviation_cost(
            Decimal("100"), Decimal("100"), Decimal("500"), self.params,
        )
        assert cost == Decimal("0")

    def test_within_exemption_band(self):
        """偏差 2%（在 3% 免考核带内）不考核。"""
        cost = self.rule.calculate_deviation_cost(
            Decimal("102"), Decimal("100"), Decimal("500"), self.params,
        )
        assert cost == Decimal("0")

    def test_exactly_at_exemption_boundary(self):
        """偏差恰好 = 3% 免考核带边界，不考核。"""
        cost = self.rule.calculate_deviation_cost(
            Decimal("103"), Decimal("100"), Decimal("500"), self.params,
        )
        assert cost == Decimal("0")

    def test_first_step_deviation(self):
        """偏差 4%，在第一阶梯 (3%-5%) 内，按 0.5 倍考核。"""
        cost = self.rule.calculate_deviation_cost(
            Decimal("104"), Decimal("100"), Decimal("500"), self.params,
        )
        # applicable_ratio = min(0.04, 0.05) - 0.03 = 0.01
        # cost = 0.01 * 100 * 500 * 0.5 = 250
        assert cost == Decimal("250")

    def test_second_step_deviation(self):
        """偏差 10%，跨越两个阶梯。"""
        cost = self.rule.calculate_deviation_cost(
            Decimal("110"), Decimal("100"), Decimal("500"), self.params,
        )
        # 第一阶梯: (min(0.10, 0.05) - 0.03) * 100 * 500 * 0.5 = 0.02 * 100 * 500 * 0.5 = 500
        # 第二阶梯: (min(0.10, 1.0) - 0.05) * 100 * 500 * 1.0 = 0.05 * 100 * 500 * 1.0 = 2500
        # 总计 = 3000
        assert cost == Decimal("3000")

    def test_forecast_zero_returns_zero(self):
        """预测值为 0 时不考核（避免除零）。"""
        cost = self.rule.calculate_deviation_cost(
            Decimal("100"), Decimal("0"), Decimal("500"), self.params,
        )
        assert cost == Decimal("0")

    def test_settlement_calculation(self):
        """结算计算：电量 × 价格。"""
        settlement = self.rule.calculate_settlement(
            Decimal("100"), Decimal("500"), {},
        )
        assert settlement == Decimal("50000")


class TestGansuDeviationCost:
    """甘肃省比例式偏差考核测试。"""

    def setup_method(self):
        self.rule = GansuRule()
        self.params = {
            "exemption_ratio": 0.05,
            "base_rate": 1.0,
        }

    def test_zero_deviation(self):
        cost = self.rule.calculate_deviation_cost(
            Decimal("100"), Decimal("100"), Decimal("500"), self.params,
        )
        assert cost == Decimal("0")

    def test_within_exemption_band(self):
        """偏差 4%（在 5% 免考核带内）不考核。"""
        cost = self.rule.calculate_deviation_cost(
            Decimal("104"), Decimal("100"), Decimal("500"), self.params,
        )
        assert cost == Decimal("0")

    def test_beyond_exemption_band(self):
        """偏差 10%，超出 5% 免考核带，按 1.0 倍考核全部偏差电量。"""
        cost = self.rule.calculate_deviation_cost(
            Decimal("110"), Decimal("100"), Decimal("500"), self.params,
        )
        # deviation_energy = 10, price = 500, base_rate = 1.0
        # cost = 10 * 500 * 1.0 = 5000
        assert cost == Decimal("5000")

    def test_forecast_zero_returns_zero(self):
        cost = self.rule.calculate_deviation_cost(
            Decimal("100"), Decimal("0"), Decimal("500"), self.params,
        )
        assert cost == Decimal("0")


class TestConfigLoader:
    def test_load_guangdong_config(self):
        config = load_province_config("guangdong")
        assert "price_cap_upper" in config
        assert config["price_cap_upper"] == 1500.00
        assert "deviation_formula_type" in config
        assert config["deviation_formula_type"] == "stepped"
        assert "deviation_formula_params" in config
        assert "exemption_ratio" in config["deviation_formula_params"]
        assert "steps" in config["deviation_formula_params"]
        assert len(config["deviation_formula_params"]["steps"]) > 0

    def test_load_gansu_config(self):
        config = load_province_config("gansu")
        assert "price_cap_upper" in config
        assert config["deviation_formula_type"] == "proportional"

    def test_load_nonexistent_returns_empty(self):
        config = load_province_config("nonexistent_province")
        assert config == {}

    def test_load_all_plugins_no_error(self):
        load_all_province_plugins()
        # 重复加载不应报错
        assert registry.get("guangdong") is not None
