from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

StationType = Literal["wind", "solar", "hybrid"]


class StationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    province: str = Field(..., min_length=1, max_length=50)
    capacity_mw: Decimal = Field(..., gt=0, le=100000, decimal_places=2)
    station_type: StationType
    has_storage: bool = False


class StationUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    province: str | None = Field(None, min_length=1, max_length=50)
    capacity_mw: Decimal | None = Field(None, gt=0, le=100000, decimal_places=2)
    station_type: StationType | None = None
    has_storage: bool | None = None
    is_active: bool | None = None


class StationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    province: str
    capacity_mw: Decimal
    station_type: StationType
    has_storage: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StationListResponse(BaseModel):
    items: list[StationRead]
    total: int
    page: int
    page_size: int
