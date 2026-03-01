from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

BatteryType = Literal["lfp", "nmc", "lto", "other"]


class StorageDeviceCreate(BaseModel):
    station_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    capacity_mwh: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    max_charge_rate_mw: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    max_discharge_rate_mw: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    soc_upper_limit: Decimal = Field(default=Decimal("0.9"), ge=0, le=1, decimal_places=4)
    soc_lower_limit: Decimal = Field(default=Decimal("0.1"), ge=0, le=1, decimal_places=4)
    battery_type: BatteryType | None = None

    @model_validator(mode="after")
    def validate_soc_range(self) -> "StorageDeviceCreate":
        if self.soc_lower_limit >= self.soc_upper_limit:
            raise ValueError("soc_lower_limit 必须小于 soc_upper_limit")
        return self


class StorageDeviceUpdate(BaseModel):
    """SOC 交叉校验在 schema 层仅校验同时提供两字段的场景。
    单字段更新时 Service 层会合并当前 DB 值进行完整交叉校验。
    """
    name: str | None = Field(None, min_length=1, max_length=100)
    capacity_mwh: Decimal | None = Field(None, gt=0, max_digits=10, decimal_places=2)
    max_charge_rate_mw: Decimal | None = Field(None, gt=0, max_digits=10, decimal_places=2)
    max_discharge_rate_mw: Decimal | None = Field(None, gt=0, max_digits=10, decimal_places=2)
    soc_upper_limit: Decimal | None = Field(None, ge=0, le=1, decimal_places=4)
    soc_lower_limit: Decimal | None = Field(None, ge=0, le=1, decimal_places=4)
    battery_type: BatteryType | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_soc_range(self) -> "StorageDeviceUpdate":
        if self.soc_lower_limit is not None and self.soc_upper_limit is not None:
            if self.soc_lower_limit >= self.soc_upper_limit:
                raise ValueError("soc_lower_limit 必须小于 soc_upper_limit")
        return self


class StorageDeviceAddInput(BaseModel):
    """子资源端点添加储能设备的输入（不含 station_id，由 URL 提供）。"""
    name: str = Field(..., min_length=1, max_length=100)
    capacity_mwh: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    max_charge_rate_mw: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    max_discharge_rate_mw: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    soc_upper_limit: Decimal = Field(default=Decimal("0.9"), ge=0, le=1, decimal_places=4)
    soc_lower_limit: Decimal = Field(default=Decimal("0.1"), ge=0, le=1, decimal_places=4)
    battery_type: BatteryType | None = None

    @model_validator(mode="after")
    def validate_soc_range(self) -> "StorageDeviceAddInput":
        if self.soc_lower_limit >= self.soc_upper_limit:
            raise ValueError("soc_lower_limit 必须小于 soc_upper_limit")
        return self


class StorageDeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    station_id: UUID
    station_name: str | None = None
    name: str
    capacity_mwh: Decimal
    max_charge_rate_mw: Decimal
    max_discharge_rate_mw: Decimal
    soc_upper_limit: Decimal
    soc_lower_limit: Decimal
    battery_type: BatteryType | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
