from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.data_access import DataAccessContext, get_data_access_context, require_write_permission
from app.core.database import get_db_session
from app.core.dependencies import require_roles
from app.core.ip_utils import get_client_ip
from app.models.user import User
from app.repositories.audit import AuditLogRepository
from app.repositories.station import StationRepository
from app.repositories.storage import StorageDeviceRepository
from app.schemas.station import (
    StationCreate,
    StationListResponse,
    StationRead,
    StationType,
    StationUpdate,
)
from app.schemas.storage import StorageDeviceRead
from app.services.audit_service import AuditService
from app.services.station_service import StationService

router = APIRouter()


def _get_station_service(session: AsyncSession = Depends(get_db_session)) -> StationService:
    station_repo = StationRepository(session)
    storage_repo = StorageDeviceRepository(session)
    audit_repo = AuditLogRepository(session)
    audit_service = AuditService(audit_repo)
    return StationService(station_repo, audit_service, storage_repo=storage_repo)


@router.get("", response_model=StationListResponse)
async def list_stations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    province: str | None = Query(None),
    station_type: StationType | None = Query(None),
    is_active: bool | None = Query(None),
    access_ctx: DataAccessContext = Depends(get_data_access_context),
    station_service: StationService = Depends(_get_station_service),
) -> StationListResponse:
    stations, total = await station_service.list_stations_for_user(
        access_ctx, page, page_size, search, province, station_type, is_active=is_active,
    )
    return StationListResponse(
        items=[StationRead.model_validate(s) for s in stations],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/active", response_model=list[StationRead])
async def list_all_active_stations(
    access_ctx: DataAccessContext = Depends(get_data_access_context),
    station_service: StationService = Depends(_get_station_service),
) -> list[StationRead]:
    """获取所有活跃电站（不分页），按用户权限过滤"""
    stations = await station_service.get_all_active_stations_for_user(access_ctx)
    return [StationRead.model_validate(s) for s in stations]


@router.get("/devices/active", response_model=list[StorageDeviceRead])
async def list_all_active_devices(
    access_ctx: DataAccessContext = Depends(get_data_access_context),
    station_service: StationService = Depends(_get_station_service),
) -> list[StorageDeviceRead]:
    """获取所有活跃储能设备，按用户权限过滤，包含所属电站名称"""
    devices, station_name_map = await station_service.get_all_active_devices_for_user(access_ctx)
    return [
        StorageDeviceRead.model_validate(d).model_copy(
            update={"station_name": station_name_map.get(str(d.station_id))},
        )
        for d in devices
    ]


@router.get("/{station_id}", response_model=StationRead)
async def get_station(
    station_id: UUID,
    access_ctx: DataAccessContext = Depends(get_data_access_context),
    station_service: StationService = Depends(_get_station_service),
) -> StationRead:
    station = await station_service.get_station_for_user(access_ctx, station_id)
    return StationRead.model_validate(station)


@router.post("", response_model=StationRead, status_code=201)
async def create_station(
    body: StationCreate,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    _write_check: User = Depends(require_write_permission),
    station_service: StationService = Depends(_get_station_service),
) -> StationRead:
    ip_address = get_client_ip(request)
    station = await station_service.create_station(current_user, body, ip_address)
    return StationRead.model_validate(station)


@router.put("/{station_id}", response_model=StationRead)
async def update_station(
    station_id: UUID,
    body: StationUpdate,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    _write_check: User = Depends(require_write_permission),
    station_service: StationService = Depends(_get_station_service),
) -> StationRead:
    ip_address = get_client_ip(request)
    station = await station_service.update_station(current_user, station_id, body, ip_address)
    return StationRead.model_validate(station)


@router.delete("/{station_id}", status_code=204)
async def delete_station(
    station_id: UUID,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    _write_check: User = Depends(require_write_permission),
    station_service: StationService = Depends(_get_station_service),
) -> None:
    ip_address = get_client_ip(request)
    await station_service.delete_station(current_user, station_id, ip_address)
