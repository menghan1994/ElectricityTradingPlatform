from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.data_access import require_write_permission
from app.core.database import get_db_session
from app.core.dependencies import require_roles
from app.core.ip_utils import get_client_ip
from app.models.user import User
from app.repositories.audit import AuditLogRepository
from app.repositories.station import StationRepository
from app.repositories.storage import StorageDeviceRepository
from app.schemas.station import StationRead
from app.schemas.storage import StorageDeviceRead
from app.schemas.wizard import StationWizardCreate, StationWizardResponse
from app.services.audit_service import AuditService
from app.services.wizard_service import WizardService

router = APIRouter()


def _get_wizard_service(session: AsyncSession = Depends(get_db_session)) -> WizardService:
    station_repo = StationRepository(session)
    storage_repo = StorageDeviceRepository(session)
    audit_repo = AuditLogRepository(session)
    audit_service = AuditService(audit_repo)
    return WizardService(station_repo, storage_repo, audit_service)


@router.post("/stations", response_model=StationWizardResponse, status_code=201)
async def create_station_with_devices(
    body: StationWizardCreate,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    _write_check: User = Depends(require_write_permission),
    wizard_service: WizardService = Depends(_get_wizard_service),
) -> StationWizardResponse:
    """向导式创建电站（含储能设备），admin-only + require_write_permission。"""
    ip_address = get_client_ip(request)
    station, devices = await wizard_service.create_station_with_devices(
        current_user, body, ip_address,
    )
    return StationWizardResponse(
        station=StationRead.model_validate(station),
        devices=[StorageDeviceRead.model_validate(d) for d in devices],
    )
