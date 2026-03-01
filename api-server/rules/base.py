from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any


class BaseRule(ABC):
    @abstractmethod
    def evaluate(self, context: dict[str, Any]) -> dict[str, Any]:
        ...


class ProvinceRule(BaseRule):
    """省份规则抽象基类 — 定义偏差考核和结算计算接口。"""

    @abstractmethod
    def calculate_deviation_cost(
        self,
        actual_mw: Decimal,
        forecast_mw: Decimal,
        price: Decimal,
        params: dict,
    ) -> Decimal:
        """计算偏差考核费用。"""
        ...

    @abstractmethod
    def calculate_settlement(
        self,
        energy_mwh: Decimal,
        price: Decimal,
        params: dict,
    ) -> Decimal:
        """计算结算金额。"""
        ...

    def evaluate(self, context: dict[str, Any]) -> dict[str, Any]:
        """通用 evaluate 接口适配。"""
        return {
            "deviation_cost": self.calculate_deviation_cost(
                Decimal(str(context["actual_mw"])),
                Decimal(str(context["forecast_mw"])),
                Decimal(str(context["price"])),
                context.get("params", {}),
            ),
        }
