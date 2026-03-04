from app.services.ems_adapters.base import BaseEmsAdapter


class StandardEmsAdapter(BaseEmsAdapter):
    """标准格式适配器 - 列名与标准格式一致，无需转换。"""

    def get_column_mapping(self) -> dict[str, str]:
        return {
            "trading_date": "trading_date",
            "period": "period",
            "soc": "soc",
            "charge_power_kw": "charge_power_kw",
            "discharge_power_kw": "discharge_power_kw",
            "cycle_count": "cycle_count",
        }
