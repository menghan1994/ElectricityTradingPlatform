from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.data_access import require_write_permission
from app.core.database import get_db_session
from app.core.dependencies import require_roles
from app.core.exceptions import BusinessError
from app.core.ip_utils import get_client_ip
from app.models.user import User
from app.repositories.audit import AuditLogRepository
from app.repositories.data_import import (
    DataImportJobRepository,
    ImportAnomalyRepository,
    TradingRecordRepository,
)
from app.repositories.station import StationRepository
from app.schemas.data_import import (
    AnomalyType,
    ImportAnomalyListResponse,
    ImportAnomalyRead,
    ImportJobListResponse,
    ImportJobRead,
    ImportJobStatus,
    ImportResultRead,
)
from app.services.audit_service import AuditService
from app.services.data_import_service import DataImportService

router = APIRouter()

ALLOWED_EXTENSIONS = {".xlsx", ".csv"}
ALLOWED_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "application/csv",
    "application/octet-stream",
}


def _get_data_import_service(
    session: AsyncSession = Depends(get_db_session),
) -> DataImportService:
    import_job_repo = DataImportJobRepository(session)
    trading_record_repo = TradingRecordRepository(session)
    anomaly_repo = ImportAnomalyRepository(session)
    station_repo = StationRepository(session)
    audit_repo = AuditLogRepository(session)
    audit_service = AuditService(audit_repo)
    return DataImportService(
        import_job_repo, trading_record_repo, anomaly_repo,
        station_repo, audit_service,
    )


def _validate_upload_file(file: UploadFile) -> None:
    """校验上传文件类型和大小。"""
    # 文件扩展名校验
    if file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise BusinessError(
                code="INVALID_FILE_TYPE",
                message=f"不支持的文件类型: {ext}，仅支持 .xlsx 和 .csv",
                status_code=422,
            )

    # Content-Type 校验（允许 application/octet-stream 作为 fallback）
    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        ext = Path(file.filename or "").suffix.lower() if file.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise BusinessError(
                code="INVALID_FILE_TYPE",
                message="不支持的文件类型，仅支持 .xlsx 和 .csv",
                status_code=422,
            )

    # 文件大小校验
    # file.size 可能为 None（chunked transfer encoding），
    # 此时由 Service 层流式写入时检查实际大小
    if file.size is not None and file.size > settings.MAX_IMPORT_FILE_SIZE:
        max_mb = settings.MAX_IMPORT_FILE_SIZE // (1024 * 1024)
        raise BusinessError(
            code="FILE_TOO_LARGE",
            message=f"文件大小超出限制，最大 {max_mb}MB",
            status_code=422,
        )


@router.post("/upload", response_model=ImportJobRead, status_code=201)
async def upload_trading_data(
    request: Request,
    file: UploadFile = File(...),
    station_id: UUID = Form(...),
    current_user: User = Depends(require_roles(["admin"])),
    _write_check: User = Depends(require_write_permission),
    service: DataImportService = Depends(_get_data_import_service),
) -> ImportJobRead:
    """上传历史交易数据文件并启动导入。"""
    _validate_upload_file(file)
    ip_address = get_client_ip(request)
    job = await service.create_import_job(station_id, file, current_user, ip_address)
    return ImportJobRead.model_validate(job)


@router.get("", response_model=ImportJobListResponse)
async def list_import_jobs(
    station_id: UUID | None = None,
    page: int = 1,
    page_size: int = 20,
    status: ImportJobStatus | None = None,
    current_user: User = Depends(require_roles(["admin"])),
    service: DataImportService = Depends(_get_data_import_service),
) -> ImportJobListResponse:
    """分页查询导入任务列表。"""
    jobs, total = await service.list_import_jobs(
        page=page, page_size=page_size, station_id=station_id, status=status,
    )
    return ImportJobListResponse(
        items=[ImportJobRead.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{job_id}", response_model=ImportJobRead)
async def get_import_job(
    job_id: UUID,
    current_user: User = Depends(require_roles(["admin"])),
    service: DataImportService = Depends(_get_data_import_service),
) -> ImportJobRead:
    """获取导入任务状态和进度。"""
    job = await service.get_import_job(job_id)
    return ImportJobRead.model_validate(job)


@router.get("/{job_id}/result", response_model=ImportResultRead)
async def get_import_result(
    job_id: UUID,
    current_user: User = Depends(require_roles(["admin"])),
    service: DataImportService = Depends(_get_data_import_service),
) -> ImportResultRead:
    """获取导入结果汇总。"""
    result = await service.get_import_result(job_id)
    return ImportResultRead(**result)


@router.get("/{job_id}/anomalies", response_model=ImportAnomalyListResponse)
async def get_import_anomalies(
    job_id: UUID,
    page: int = 1,
    page_size: int = 20,
    anomaly_type: AnomalyType | None = None,
    current_user: User = Depends(require_roles(["admin"])),
    service: DataImportService = Depends(_get_data_import_service),
) -> ImportAnomalyListResponse:
    """分页查询异常记录。"""
    anomalies, total = await service.get_anomalies(
        job_id=job_id, page=page, page_size=page_size, anomaly_type=anomaly_type,
    )
    return ImportAnomalyListResponse(
        items=[ImportAnomalyRead.model_validate(a) for a in anomalies],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/{job_id}/resume", response_model=ImportJobRead)
async def resume_import(
    job_id: UUID,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    _write_check: User = Depends(require_write_permission),
    service: DataImportService = Depends(_get_data_import_service),
) -> ImportJobRead:
    """恢复中断的导入任务。"""
    ip_address = get_client_ip(request)
    job = await service.resume_import_job(job_id, current_user, ip_address)
    return ImportJobRead.model_validate(job)


@router.post("/{job_id}/cancel", response_model=ImportJobRead)
async def cancel_import(
    job_id: UUID,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    _write_check: User = Depends(require_write_permission),
    service: DataImportService = Depends(_get_data_import_service),
) -> ImportJobRead:
    """取消正在运行的导入任务。"""
    ip_address = get_client_ip(request)
    job = await service.cancel_import_job(job_id, current_user, ip_address)
    return ImportJobRead.model_validate(job)
