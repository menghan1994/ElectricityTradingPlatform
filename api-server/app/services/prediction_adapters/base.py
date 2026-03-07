from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class PredictionRecord:
    period: int  # 1-96
    predicted_power_kw: Decimal  # 预测功率 kW
    confidence_upper_kw: Decimal  # 置信区间上限 kW
    confidence_lower_kw: Decimal  # 置信区间下限 kW


class BasePredictionAdapter(ABC):
    """功率预测模型适配器基类。"""

    @abstractmethod
    async def fetch_predictions(
        self, station_id: str, prediction_date: date,
    ) -> list[PredictionRecord]:
        """获取指定电站指定日期的96时段功率预测。"""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """检查预测模型API可用性。"""
        ...

    def get_adapter_info(self) -> dict:
        """返回适配器名称、版本、支持的模型类型。"""
        return {
            "name": self.__class__.__name__,
            "version": "1.0.0",
            "supported_types": ["wind", "solar", "hybrid"],
        }
