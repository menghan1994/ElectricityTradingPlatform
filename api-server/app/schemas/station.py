from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

StationType = Literal["wind", "solar", "hybrid"]

# H6: 省份服务端校验 — 限定合法省份拼音值
Province = Literal[
    "gansu", "qinghai", "ningxia", "xinjiang", "neimenggu",
    "hebei", "shandong", "guangdong", "yunnan", "sichuan",
    "shanxi", "jiangsu", "liaoning", "jilin", "heilongjiang",
    "henan", "hubei", "hunan", "anhui", "fujian",
    "zhejiang", "jiangxi", "guizhou", "xizang", "hainan",
    "guangxi", "chongqing", "beijing", "tianjin", "shanghai",
    "shaanxi",
]


class _GridConnectionPointMixin:
    """H3: 空字符串转 None，防止存入空串。"""

    @field_validator("grid_connection_point", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: str | None) -> str | None:
        if isinstance(v, str) and not v.strip():
            return None
        return v


class StationCreate(_GridConnectionPointMixin, BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    province: Province
    capacity_mw: Decimal = Field(..., gt=0, le=100000, decimal_places=2)
    station_type: StationType
    grid_connection_point: str | None = Field(None, max_length=200)
    # H2: has_storage 不暴露给非向导创建路径 — 始终从 False 开始，
    # 通过向导或设备增删自动同步


class StationUpdate(_GridConnectionPointMixin, BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    province: Province | None = None
    capacity_mw: Decimal | None = Field(None, gt=0, le=100000, decimal_places=2)
    station_type: StationType | None = None
    grid_connection_point: str | None = Field(None, max_length=200)
    # C1: has_storage 不允许直接修改 — 仅通过 WizardService 的设备增删自动同步
    is_active: bool | None = None


class StationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    province: str
    capacity_mw: Decimal
    station_type: StationType
    grid_connection_point: str | None = None
    has_storage: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StationListResponse(BaseModel):
    items: list[StationRead]
    total: int
    page: int
    page_size: int
