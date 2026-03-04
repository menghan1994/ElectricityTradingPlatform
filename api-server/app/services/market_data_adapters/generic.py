import asyncio
from datetime import date
from decimal import Decimal

import httpx
import structlog

from app.core.config import settings
from app.services.market_data_adapters.base import BaseMarketDataAdapter, MarketPriceRecord

logger = structlog.get_logger()


class GenericMarketDataAdapter(BaseMarketDataAdapter):
    """通用市场数据适配器 - 标准 JSON API 格式。

    期望 API 返回格式:
    {
        "data": [
            {"period": 1, "clearing_price": 350.00},
            {"period": 2, "clearing_price": 345.50},
            ...
        ]
    }
    """

    def __init__(
        self,
        api_endpoint: str,
        api_key: str | None = None,
        api_auth_type: str = "api_key",
    ):
        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.api_auth_type = api_auth_type

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.api_key:
            if self.api_auth_type == "bearer":
                headers["Authorization"] = f"Bearer {self.api_key}"
            elif self.api_auth_type == "api_key":
                headers["X-API-Key"] = self.api_key
        return headers

    async def fetch(self, trading_date: date) -> list[MarketPriceRecord]:
        """从外部 API 获取出清价格，含重试逻辑（最多2次，指数退避）。"""
        params = {"trading_date": trading_date.isoformat()}
        headers = self._build_headers()
        last_error: Exception | None = None

        for attempt in range(1, settings.MARKET_DATA_RETRY_COUNT + 2):
            try:
                async with httpx.AsyncClient(
                    timeout=settings.MARKET_DATA_FETCH_TIMEOUT,
                ) as client:
                    response = await client.get(
                        self.api_endpoint,
                        params=params,
                        headers=headers,
                    )
                    response.raise_for_status()
                    data = response.json()
                    return self._parse_response(trading_date, data)
            except (httpx.HTTPError, KeyError, ValueError) as e:
                last_error = e
                logger.warning(
                    "market_data_fetch_attempt_failed",
                    attempt=attempt,
                    error=str(e),
                    endpoint=self.api_endpoint,
                    trading_date=trading_date.isoformat(),
                )
                if attempt <= settings.MARKET_DATA_RETRY_COUNT:
                    backoff = settings.MARKET_DATA_RETRY_BACKOFF * (2 ** (attempt - 1))
                    await asyncio.sleep(backoff)

        raise RuntimeError(
            f"市场数据获取失败（已重试{settings.MARKET_DATA_RETRY_COUNT}次）: {last_error}"
        )

    def _parse_response(self, trading_date: date, data: dict) -> list[MarketPriceRecord]:
        records = []
        items = data.get("data", [])
        for item in items:
            period = int(item["period"])
            clearing_price = Decimal(str(item["clearing_price"]))
            records.append(
                MarketPriceRecord(
                    trading_date=trading_date,
                    period=period,
                    clearing_price=clearing_price,
                )
            )
        return records

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.head(
                    self.api_endpoint,
                    headers=self._build_headers(),
                )
                return response.status_code < 500
        except httpx.HTTPError:
            return False
