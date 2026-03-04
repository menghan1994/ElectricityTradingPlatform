from decimal import Decimal

from app.services.ems_adapters.base import BaseEmsAdapter


class SungrowEmsAdapter(BaseEmsAdapter):
    """阳光电源 EMS 格式适配器。

    特殊处理:
    - SOC 为百分比 (0-100)，需除以 100 转换为小数 (0-1)
    - 列名使用中文
    """

    def get_column_mapping(self) -> dict[str, str]:
        return {
            "数据日期": "trading_date",
            "时段序号": "period",
            "SOC(%)": "soc",
            "充电功率(kW)": "charge_power_kw",
            "放电功率(kW)": "discharge_power_kw",
            "累计循环": "cycle_count",
        }

    def transform_soc(self, value: str | float | Decimal) -> Decimal:
        """阳光电源 SOC 为百分比 (0-100)，需转换为小数 (0-1)。"""
        return Decimal(str(value)) / Decimal("100")
