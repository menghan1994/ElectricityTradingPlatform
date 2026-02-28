from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.station import StationRead
from app.schemas.storage import StorageDeviceRead

# HIGH-5: 拆分为独立 schema，防止向 station 端点发送 device_ids 导致静默清空绑定
MAX_BINDING_IDS = 500  # LOW: 绑定 ID 列表长度上限


class StationBindingBatchUpdate(BaseModel):
    """全量替换用户-电站绑定关系"""
    station_ids: list[UUID] = Field(default_factory=list, max_length=MAX_BINDING_IDS)


class DeviceBindingBatchUpdate(BaseModel):
    """全量替换用户-设备绑定关系"""
    device_ids: list[UUID] = Field(default_factory=list, max_length=MAX_BINDING_IDS)


class UserStationBindingsRead(BaseModel):
    station_ids: list[UUID]
    stations: list[StationRead]


class UserDeviceBindingsRead(BaseModel):
    device_ids: list[UUID]
    devices: list[StorageDeviceRead]
