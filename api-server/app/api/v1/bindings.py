from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import require_roles
from app.core.ip_utils import get_client_ip
from app.models.user import User
from app.repositories.audit import AuditLogRepository
from app.repositories.binding import BindingRepository
from app.repositories.station import StationRepository
from app.repositories.storage import StorageDeviceRepository
from app.repositories.user import UserRepository
from app.schemas.binding import (
    DeviceBindingBatchUpdate,
    StationBindingBatchUpdate,
    UserDeviceBindingsRead,
    UserStationBindingsRead,
)
from app.schemas.station import StationRead
from app.schemas.storage import StorageDeviceRead
from app.services.audit_service import AuditService
from app.services.binding_service import BindingService

router = APIRouter()


def _get_binding_service(session: AsyncSession = Depends(get_db_session)) -> BindingService:
    binding_repo = BindingRepository(session)
    station_repo = StationRepository(session)
    storage_repo = StorageDeviceRepository(session)
    user_repo = UserRepository(session)
    audit_repo = AuditLogRepository(session)
    audit_service = AuditService(audit_repo)
    return BindingService(binding_repo, station_repo, storage_repo, user_repo, audit_service)


# ── 电站绑定 ──

@router.get(
    "/{user_id}/station_bindings",
    response_model=UserStationBindingsRead,
)
async def get_user_station_bindings(
    user_id: UUID,
    current_user: User = Depends(require_roles(["admin"])),
    binding_service: BindingService = Depends(_get_binding_service),
) -> UserStationBindingsRead:
    station_ids, stations = await binding_service.get_user_station_bindings(user_id)
    return UserStationBindingsRead(
        station_ids=station_ids,
        stations=[StationRead.model_validate(s) for s in stations],
    )


@router.put(
    "/{user_id}/station_bindings",
    response_model=UserStationBindingsRead,
)
async def update_user_station_bindings(
    user_id: UUID,
    body: StationBindingBatchUpdate,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    binding_service: BindingService = Depends(_get_binding_service),
) -> UserStationBindingsRead:
    ip_address = get_client_ip(request)
    station_ids, stations = await binding_service.update_user_station_bindings(
        current_user, user_id, body.station_ids, ip_address,
    )
    return UserStationBindingsRead(
        station_ids=station_ids,
        stations=[StationRead.model_validate(s) for s in stations],
    )


# ── 设备绑定 ──

@router.get(
    "/{user_id}/device_bindings",
    response_model=UserDeviceBindingsRead,
)
async def get_user_device_bindings(
    user_id: UUID,
    current_user: User = Depends(require_roles(["admin"])),
    binding_service: BindingService = Depends(_get_binding_service),
) -> UserDeviceBindingsRead:
    device_ids, devices = await binding_service.get_user_device_bindings(user_id)
    return UserDeviceBindingsRead(
        device_ids=device_ids,
        devices=[StorageDeviceRead.model_validate(d) for d in devices],
    )


@router.put(
    "/{user_id}/device_bindings",
    response_model=UserDeviceBindingsRead,
)
async def update_user_device_bindings(
    user_id: UUID,
    body: DeviceBindingBatchUpdate,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    binding_service: BindingService = Depends(_get_binding_service),
) -> UserDeviceBindingsRead:
    ip_address = get_client_ip(request)
    device_ids, devices = await binding_service.update_user_device_bindings(
        current_user, user_id, body.device_ids, ip_address,
    )
    return UserDeviceBindingsRead(
        device_ids=device_ids,
        devices=[StorageDeviceRead.model_validate(d) for d in devices],
    )
