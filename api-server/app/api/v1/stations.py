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
from app.schemas.storage import StorageDeviceAddInput, StorageDeviceRead, StorageDeviceUpdate
from app.services.audit_service import AuditService
from app.services.station_service import StationService
from app.services.wizard_service import WizardService  # noqa: TC002 — 端点类型注解需要
# M2: 复用 wizard 模块的工厂函数，避免重复定义
from app.api.v1.wizard import _get_wizard_service

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


# ── 储能设备子资源端点 ──


@router.get("/{station_id}/devices", response_model=list[StorageDeviceRead])
async def list_station_devices(
    station_id: UUID,
    access_ctx: DataAccessContext = Depends(get_data_access_context),
    station_service: StationService = Depends(_get_station_service),
) -> list[StorageDeviceRead]:
    """获取指定电站下所有储能设备。"""
    # C1: 使用 access_ctx 过滤电站访问权限（修复 IDOR）
    await station_service.get_station_for_user(access_ctx, station_id)
    _, devices = await station_service.get_station_with_devices(station_id)
    return [StorageDeviceRead.model_validate(d) for d in devices]


@router.post("/{station_id}/devices", response_model=StorageDeviceRead, status_code=201)
async def add_device_to_station(
    station_id: UUID,
    body: StorageDeviceAddInput,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    _write_check: User = Depends(require_write_permission),
    wizard_service: WizardService = Depends(_get_wizard_service),
) -> StorageDeviceRead:
    """向已有电站添加储能设备。"""
    # C2: 业务逻辑委托 WizardService（含 is_active 检查、has_storage 同步、完整审计）
    ip_address = get_client_ip(request)
    created = await wizard_service.add_device_to_station(
        current_user, station_id, body, ip_address,
    )
    return StorageDeviceRead.model_validate(created)


@router.put("/{station_id}/devices/{device_id}", response_model=StorageDeviceRead)
async def update_station_device(
    station_id: UUID,
    device_id: UUID,
    body: StorageDeviceUpdate,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    _write_check: User = Depends(require_write_permission),
    wizard_service: WizardService = Depends(_get_wizard_service),
) -> StorageDeviceRead:
    """更新储能设备参数（支持 SOC 单字段更新完整交叉校验）。"""
    ip_address = get_client_ip(request)
    update_data = body.model_dump(exclude_unset=True)
    device = await wizard_service.update_storage_device(
        current_user, station_id, device_id, update_data, ip_address,
    )
    return StorageDeviceRead.model_validate(device)


@router.delete("/{station_id}/devices/{device_id}", status_code=204)
async def delete_station_device(
    station_id: UUID,
    device_id: UUID,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    _write_check: User = Depends(require_write_permission),
    wizard_service: WizardService = Depends(_get_wizard_service),
) -> None:
    """删除储能设备（软删除）。"""
    # C2: 业务逻辑委托 WizardService（含 is_active 检查、has_storage 同步）
    ip_address = get_client_ip(request)
    await wizard_service.delete_station_device(
        current_user, station_id, device_id, ip_address,
    )
