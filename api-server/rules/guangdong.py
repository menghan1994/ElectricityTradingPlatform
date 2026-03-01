from decimal import Decimal

from rules.base import ProvinceRule
from rules.registry import register_province


@register_province("guangdong")
class GuangdongRule(ProvinceRule):
    """广东省规则 — 阶梯式偏差考核。

    免考核带 ±exemption_ratio，超出部分按阶梯 rate 计算考核费用。
    """

    def calculate_deviation_cost(
        self,
        actual_mw: Decimal,
        forecast_mw: Decimal,
        price: Decimal,
        params: dict,
    ) -> Decimal:
        if forecast_mw == 0:
            return Decimal("0")

        deviation_ratio = abs(actual_mw - forecast_mw) / forecast_mw
        exemption_ratio = Decimal(str(params.get("exemption_ratio", "0.03")))

        if deviation_ratio <= exemption_ratio:
            return Decimal("0")

        total_cost = Decimal("0")
        steps = params.get("steps", [])

        for step in steps:
            lower = Decimal(str(step["lower"]))
            upper = Decimal(str(step["upper"]))
            rate = Decimal(str(step["rate"]))

            if deviation_ratio <= lower:
                break

            applicable_ratio = min(deviation_ratio, upper) - lower
            if applicable_ratio > 0:
                total_cost += applicable_ratio * forecast_mw * price * rate

        return total_cost

    def calculate_settlement(
        self,
        energy_mwh: Decimal,
        price: Decimal,
        params: dict,
    ) -> Decimal:
        return energy_mwh * price
