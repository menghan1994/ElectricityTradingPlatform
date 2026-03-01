from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.schemas.station import Province, StationRead, StationType, _GridConnectionPointMixin
from app.schemas.storage import BatteryType, StorageDeviceRead


class WizardStorageDeviceInput(BaseModel):
    """向导中储能设备的输入参数（不含 station_id，由向导自动关联）。"""
    name: str = Field(..., min_length=1, max_length=100)
    capacity_mwh: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    max_charge_rate_mw: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    max_discharge_rate_mw: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    soc_upper_limit: Decimal = Field(default=Decimal("0.9"), ge=0, le=1, decimal_places=4)
    soc_lower_limit: Decimal = Field(default=Decimal("0.1"), ge=0, le=1, decimal_places=4)
    battery_type: BatteryType | None = None

    @model_validator(mode="after")
    def validate_soc_range(self) -> "WizardStorageDeviceInput":
        if self.soc_lower_limit >= self.soc_upper_limit:
            raise ValueError("soc_lower_limit 必须小于 soc_upper_limit")
        return self


class StationWizardCreate(_GridConnectionPointMixin, BaseModel):
    """向导式创建电站（含可选储能设备）的请求体。"""
    name: str = Field(..., min_length=1, max_length=100)
    province: Province
    capacity_mw: Decimal = Field(..., gt=0, le=100000, decimal_places=2)
    station_type: StationType
    grid_connection_point: str | None = Field(None, max_length=200)
    has_storage: bool = False
    storage_devices: list[WizardStorageDeviceInput] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_storage_consistency(self) -> "StationWizardCreate":
        if self.has_storage and not self.storage_devices:
            raise ValueError("has_storage 为 true 时必须提供至少一个储能设备")
        if not self.has_storage and self.storage_devices:
            raise ValueError("has_storage 为 false 时不应提供储能设备")
        # C4+M1: 设备名称去重校验（大小写不敏感）
        if self.storage_devices:
            names = [d.name.lower() for d in self.storage_devices]
            if len(names) != len(set(names)):
                raise ValueError("储能设备名称不能重复")
        return self


class StationWizardResponse(BaseModel):
    """向导创建电站的响应体。"""
    station: StationRead
    devices: list[StorageDeviceRead]
