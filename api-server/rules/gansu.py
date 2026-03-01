from decimal import Decimal

from rules.base import ProvinceRule
from rules.registry import register_province


@register_province("gansu")
class GansuRule(ProvinceRule):
    """甘肃省规则 — 比例式偏差考核。

    免考核带 ±exemption_ratio，超出部分按 base_rate 乘以全部偏差电量。
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
        deviation_energy = abs(actual_mw - forecast_mw)
        exemption_ratio = Decimal(str(params.get("exemption_ratio", "0.05")))
        base_rate = Decimal(str(params.get("base_rate", "1.0")))

        if deviation_ratio <= exemption_ratio:
            return Decimal("0")

        return deviation_energy * price * base_rate

    def calculate_settlement(
        self,
        energy_mwh: Decimal,
        price: Decimal,
        params: dict,
    ) -> Decimal:
        return energy_mwh * price
