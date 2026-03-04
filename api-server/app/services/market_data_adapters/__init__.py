from app.services.market_data_adapters.base import BaseMarketDataAdapter, MarketPriceRecord
from app.services.market_data_adapters.generic import GenericMarketDataAdapter


def get_adapter(
    api_endpoint: str,
    api_key: str | None = None,
    api_auth_type: str = "api_key",
) -> BaseMarketDataAdapter:
    """根据配置返回适配器实例。

    MVP 阶段仅支持通用 JSON API 适配器。
    后续省份可通过新增适配器类并在此工厂方法中路由来扩展。
    """
    return GenericMarketDataAdapter(
        api_endpoint=api_endpoint,
        api_key=api_key,
        api_auth_type=api_auth_type,
    )
