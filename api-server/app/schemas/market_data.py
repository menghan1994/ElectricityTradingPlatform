from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

PERIODS_PER_DAY = 96

FreshnessStatus = Literal["fresh", "stale", "expired", "critical"]
FetchStatus = Literal["pending", "success", "failed"]
PriceSource = Literal["api", "manual_import"]
ApiAuthType = Literal["api_key", "bearer", "none"]


# --- 出清价格 schemas ---


class MarketClearingPriceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trading_date: date
    period: int
    province: str
    clearing_price: Decimal
    source: PriceSource
    fetched_at: datetime
    import_job_id: UUID | None
    created_at: datetime


class MarketClearingPriceListResponse(BaseModel):
    items: list[MarketClearingPriceRead]
    total: int
    page: int
    page_size: int


# --- 数据源配置 schemas ---


class MarketDataSourceCreate(BaseModel):
    province: str
    source_name: str
    api_endpoint: str | None = None
    api_key: str | None = None
    api_auth_type: ApiAuthType = "api_key"
    fetch_schedule: str = "0 7,12,17 * * *"
    is_active: bool = True
    cache_ttl_seconds: int = 3600

    @field_validator("province")
    @classmethod
    def validate_province(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("省份标识不能为空")
        return v.strip()

    @field_validator("cache_ttl_seconds")
    @classmethod
    def validate_cache_ttl(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("缓存TTL必须大于0")
        return v


class MarketDataSourceUpdate(BaseModel):
    source_name: str | None = None
    api_endpoint: str | None = None
    api_key: str | None = None
    api_auth_type: ApiAuthType | None = None
    fetch_schedule: str | None = None
    is_active: bool | None = None
    cache_ttl_seconds: int | None = None

    @field_validator("cache_ttl_seconds")
    @classmethod
    def validate_cache_ttl(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("缓存TTL必须大于0")
        return v


class MarketDataSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    province: str
    source_name: str
    api_endpoint: str | None
    api_auth_type: ApiAuthType
    fetch_schedule: str
    is_active: bool
    last_fetch_at: datetime | None
    last_fetch_status: FetchStatus
    last_fetch_error: str | None
    cache_ttl_seconds: int
    created_at: datetime
    updated_at: datetime


class MarketDataSourceListResponse(BaseModel):
    items: list[MarketDataSourceRead]
    total: int
    page: int
    page_size: int


# --- 数据新鲜度 schemas ---


class MarketDataFreshness(BaseModel):
    province: str
    last_updated: datetime | None
    hours_ago: float | None
    status: FreshnessStatus


class MarketDataFreshnessListResponse(BaseModel):
    items: list[MarketDataFreshness]


# --- 获取结果 schemas ---


class MarketDataFetchResult(BaseModel):
    province: str
    trading_date: date
    records_count: int
    status: str
    error_message: str | None = None
