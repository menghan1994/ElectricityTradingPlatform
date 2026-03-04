from decimal import Decimal

from app.services.ems_adapters.base import BaseEmsAdapter


class CatlEmsAdapter(BaseEmsAdapter):
    """宁德时代 EMS 格式适配器。

    列名使用英文 snake_case，与标准格式不同。
    SOC 列名为 soc_pct，值为百分比(0-100)，需要转换为小数(0.0-1.0)。
    """

    def get_column_mapping(self) -> dict[str, str]:
        return {
            "record_date": "trading_date",
            "period_no": "period",
            "soc_pct": "soc",
            "charge_kw": "charge_power_kw",
            "discharge_kw": "discharge_power_kw",
            "total_cycles": "cycle_count",
        }

    def transform_soc(self, value: str | float | Decimal) -> Decimal:
        """将百分比 SOC (0-100) 转换为小数格式 (0.0-1.0)。"""
        return Decimal(str(value)) / Decimal("100")
