from abc import ABC, abstractmethod
from decimal import Decimal


class BaseEmsAdapter(ABC):
    """EMS 数据格式适配器基类。

    每个适配器负责将厂商特有的列名、数据格式、单位转换为标准格式。
    """

    @abstractmethod
    def get_column_mapping(self) -> dict[str, str]:
        """返回厂商列名到标准列名的映射。

        标准列名:
        - trading_date: 交易日期
        - period: 时段编号 (1-96)
        - soc: SOC (0.0-1.0)
        - charge_power_kw: 充电功率 kW
        - discharge_power_kw: 放电功率 kW
        - cycle_count: 循环次数
        """
        ...

    def transform_soc(self, value: str | float | Decimal) -> Decimal:
        """将 SOC 值转换为标准格式 (0.0-1.0)。默认直接解析为 Decimal。"""
        return Decimal(str(value))

    def transform_power(self, value: str | float | Decimal) -> Decimal:
        """将功率值转换为 kW。默认直接解析为 Decimal。"""
        return Decimal(str(value))

    def transform_cycle_count(self, value: str | int) -> int:
        """将循环次数转换为整数。"""
        return int(value)
