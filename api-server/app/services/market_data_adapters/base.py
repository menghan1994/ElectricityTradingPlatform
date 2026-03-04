from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class MarketPriceRecord:
    trading_date: date
    period: int  # 1-96
    clearing_price: Decimal  # 元/MWh


class BaseMarketDataAdapter(ABC):
    """市场数据适配器基类 - 省级交易中心 API 接入。"""

    @abstractmethod
    async def fetch(self, trading_date: date) -> list[MarketPriceRecord]:
        """获取指定交易日的96时段出清价格。"""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """检查 API 可用性。"""
        ...
