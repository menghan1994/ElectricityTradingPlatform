from app.services.ems_adapters.base import BaseEmsAdapter


class HuaweiEmsAdapter(BaseEmsAdapter):
    """华为 EMS 格式适配器。

    列名使用英文 PascalCase。
    SOC 已为小数格式，无需特殊转换。
    """

    def get_column_mapping(self) -> dict[str, str]:
        return {
            "Date": "trading_date",
            "TimeSlot": "period",
            "BatterySOC": "soc",
            "ChargePower": "charge_power_kw",
            "DischargePower": "discharge_power_kw",
            "CycleCount": "cycle_count",
        }
