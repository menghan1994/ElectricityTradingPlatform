import asyncio
from datetime import date
from decimal import Decimal

import httpx
import structlog

from app.services.prediction_adapters.base import BasePredictionAdapter, PredictionRecord

logger = structlog.get_logger()

HEALTH_CHECK_TIMEOUT = 5
MAX_RETRIES = 2
INITIAL_BACKOFF = 1.0


class GenericPredictionAdapter(BasePredictionAdapter):
    """通用功率预测适配器 - 标准 JSON API 格式。

    期望 API 返回格式:
    [
        {
            "period": 1,
            "predicted_power_kw": 1500.00,
            "confidence_upper_kw": 1650.00,
            "confidence_lower_kw": 1350.00
        },
        ...
    ]
    """

    def __init__(
        self,
        api_endpoint: str,
        api_key: str | None = None,
        api_auth_type: str = "api_key",
        timeout_seconds: int = 30,
    ):
        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.api_auth_type = api_auth_type
        self.timeout_seconds = timeout_seconds

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.api_key:
            if self.api_auth_type == "bearer":
                headers["Authorization"] = f"Bearer {self.api_key}"
            elif self.api_auth_type == "api_key":
                headers["X-API-Key"] = self.api_key
        return headers

    async def fetch_predictions(
        self, station_id: str, prediction_date: date,
    ) -> list[PredictionRecord]:
        """从外部 API 获取功率预测，含重试逻辑（最多2次，指数退避 1s→2s）。"""
        params = {
            "station_id": station_id,
            "prediction_date": prediction_date.isoformat(),
        }
        headers = self._build_headers()
        last_error: Exception | None = None

        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
        ) as client:
            for attempt in range(1, MAX_RETRIES + 2):
                try:
                    response = await client.get(
                        self.api_endpoint,
                        params=params,
                        headers=headers,
                    )
                    response.raise_for_status()
                    data = response.json()
                    return self._parse_response(data)
                except (httpx.HTTPError, KeyError, ValueError) as e:
                    last_error = e
                    logger.warning(
                        "prediction_fetch_attempt_failed",
                        attempt=attempt,
                        error=str(e),
                        endpoint=self.api_endpoint,
                        station_id=station_id,
                        prediction_date=prediction_date.isoformat(),
                    )
                    if attempt <= MAX_RETRIES:
                        backoff = INITIAL_BACKOFF * (2 ** (attempt - 1))
                        await asyncio.sleep(backoff)

        raise RuntimeError(
            f"功率预测获取失败（已重试{MAX_RETRIES}次）: {last_error}"
        )

    def _parse_response(self, data: list | dict) -> list[PredictionRecord]:
        items = data if isinstance(data, list) else data.get("data", [])
        records = []
        for item in items:
            records.append(
                PredictionRecord(
                    period=int(item["period"]),
                    predicted_power_kw=Decimal(str(item["predicted_power_kw"])),
                    confidence_upper_kw=Decimal(str(item["confidence_upper_kw"])),
                    confidence_lower_kw=Decimal(str(item["confidence_lower_kw"])),
                )
            )
        return records

    async def health_check(self) -> bool:
        """检查预测模型 API 可用性，超时5秒。"""
        try:
            async with httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT) as client:
                response = await asyncio.wait_for(
                    client.head(
                        self.api_endpoint,
                        headers=self._build_headers(),
                    ),
                    timeout=HEALTH_CHECK_TIMEOUT,
                )
                return response.status_code < 500
        except (httpx.HTTPError, asyncio.TimeoutError):
            return False
