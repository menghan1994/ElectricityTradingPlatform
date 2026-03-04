from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import require_roles
from app.core.ip_utils import get_client_ip
from app.models.user import User
from app.repositories.audit import AuditLogRepository
from app.repositories.data_import import (
    DataImportJobRepository,
    ImportAnomalyRepository,
    StationOutputRepository,
    StorageOperationRepository,
    TradingRecordRepository,
)
from app.repositories.station import StationRepository
from app.repositories.storage import StorageDeviceRepository
from app.schemas.data_import import (
    AnomalyBulkActionRequest,
    AnomalyBulkActionResponse,
    AnomalyCorrectRequest,
    AnomalyDetailRead,
    AnomalyStatus,
    AnomalyType,
    ImportAnomalyListResponse,
    ImportAnomalySummary,
    ImportAnomalyRead,
)
from app.services.audit_service import AuditService
from app.services.data_import_service import DataImportService

router = APIRouter()


def _get_data_import_service(
    session: AsyncSession = Depends(get_db_session),
) -> DataImportService:
    import_job_repo = DataImportJobRepository(session)
    trading_record_repo = TradingRecordRepository(session)
    anomaly_repo = ImportAnomalyRepository(session)
    station_repo = StationRepository(session)
    audit_repo = AuditLogRepository(session)
    audit_service = AuditService(audit_repo)
    station_output_repo = StationOutputRepository(session)
    storage_operation_repo = StorageOperationRepository(session)
    storage_device_repo = StorageDeviceRepository(session)
    return DataImportService(
        import_job_repo, trading_record_repo, anomaly_repo,
        station_repo, audit_service,
        station_output_repo=station_output_repo,
        storage_operation_repo=storage_operation_repo,
        storage_device_repo=storage_device_repo,
    )


@router.get("", response_model=ImportAnomalyListResponse)
async def list_anomalies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    anomaly_type: AnomalyType | None = None,
    status: AnomalyStatus | None = None,
    import_job_id: UUID | None = None,
    current_user: User = Depends(require_roles(["admin"])),
    service: DataImportService = Depends(_get_data_import_service),
) -> ImportAnomalyListResponse:
    """全局异常列表（跨导入批次），支持三重筛选。"""
    anomalies, total = await service.list_anomalies_global(
        page=page,
        page_size=page_size,
        anomaly_type=anomaly_type,
        status=status,
        import_job_id=import_job_id,
    )
    return ImportAnomalyListResponse(
        items=[ImportAnomalyRead.model_validate(a) for a in anomalies],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/summary", response_model=list[ImportAnomalySummary])
async def get_anomaly_summary(
    import_job_id: UUID | None = None,
    status: AnomalyStatus | None = "pending",
    current_user: User = Depends(require_roles(["admin"])),
    service: DataImportService = Depends(_get_data_import_service),
) -> list[ImportAnomalySummary]:
    """异常分类统计。"""
    summary = await service.get_anomaly_summary(
        import_job_id=import_job_id,
        status=status,
    )
    return [ImportAnomalySummary(**s) for s in summary]


@router.get("/{anomaly_id}", response_model=AnomalyDetailRead)
async def get_anomaly(
    anomaly_id: UUID,
    current_user: User = Depends(require_roles(["admin"])),
    service: DataImportService = Depends(_get_data_import_service),
) -> AnomalyDetailRead:
    """获取单条异常详情。"""
    detail = await service.get_anomaly_detail(anomaly_id)
    data = AnomalyDetailRead.model_validate(detail["anomaly"])
    data.original_file_name = detail["original_file_name"]
    data.station_id = detail["station_id"]
    return data


@router.patch("/{anomaly_id}/correct", response_model=ImportAnomalyRead)
async def correct_anomaly(
    anomaly_id: UUID,
    body: AnomalyCorrectRequest,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    service: DataImportService = Depends(_get_data_import_service),
) -> ImportAnomalyRead:
    """修正异常数据。"""
    ip_address = get_client_ip(request)
    anomaly = await service.correct_anomaly(
        anomaly_id, body.corrected_value, current_user, ip_address,
    )
    return ImportAnomalyRead.model_validate(anomaly)


@router.patch("/{anomaly_id}/confirm-normal", response_model=ImportAnomalyRead)
async def confirm_anomaly_normal(
    anomaly_id: UUID,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    service: DataImportService = Depends(_get_data_import_service),
) -> ImportAnomalyRead:
    """标记异常为已确认正常。"""
    ip_address = get_client_ip(request)
    anomaly = await service.confirm_anomaly_normal(
        anomaly_id, current_user, ip_address,
    )
    return ImportAnomalyRead.model_validate(anomaly)


@router.post("/bulk-action", response_model=AnomalyBulkActionResponse)
async def bulk_action(
    body: AnomalyBulkActionRequest,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    service: DataImportService = Depends(_get_data_import_service),
) -> AnomalyBulkActionResponse:
    """批量操作异常数据（删除或确认正常）。"""
    ip_address = get_client_ip(request)

    if body.action == "delete":
        affected = await service.bulk_delete_anomalies(
            body.anomaly_ids, current_user, ip_address,
        )
    else:
        affected = await service.bulk_confirm_normal(
            body.anomaly_ids, current_user, ip_address,
        )

    return AnomalyBulkActionResponse(
        affected_count=affected,
        action=body.action,
    )
