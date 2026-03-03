import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import structlog
from fastapi import UploadFile
from sqlalchemy import select

from app.core.config import settings
from app.core.exceptions import BusinessError
from app.models.data_import import DataImportJob
from app.models.station import PowerStation
from app.models.user import User
from app.repositories.data_import import (
    DataImportJobRepository,
    ImportAnomalyRepository,
    TradingRecordRepository,
)
from app.repositories.station import StationRepository
from app.services.audit_service import AuditService

logger = structlog.get_logger()

# 文件名白名单：仅允许字母、数字、中文、下划线、连字符、点号、空格
_SAFE_FILENAME_RE = re.compile(r"[^\w\.\-\s\u4e00-\u9fff]", re.UNICODE)

# 流式写入块大小 (64KB)
_UPLOAD_CHUNK_SIZE = 64 * 1024


class DataImportService:
    def __init__(
        self,
        import_job_repo: DataImportJobRepository,
        trading_record_repo: TradingRecordRepository,
        anomaly_repo: ImportAnomalyRepository,
        station_repo: StationRepository,
        audit_service: AuditService,
    ):
        self.import_job_repo = import_job_repo
        self.trading_record_repo = trading_record_repo
        self.anomaly_repo = anomaly_repo
        self.station_repo = station_repo
        self.audit_service = audit_service

    def _warn_if_no_ip(self, action: str, ip_address: str | None) -> None:
        if ip_address is None:
            logger.warning("audit_ip_missing", action=action, hint="非 HTTP 上下文调用，IP 地址缺失")

    async def create_import_job(
        self,
        station_id: UUID,
        file: UploadFile,
        current_user: User,
        client_ip: str | None = None,
    ) -> DataImportJob:
        self._warn_if_no_ip("create_import_job", client_ip)

        # 锁定电站行，序列化同一电站的并发导入请求
        stmt = (
            select(PowerStation)
            .where(PowerStation.id == station_id)
            .with_for_update()
        )
        result = await self.station_repo.session.execute(stmt)
        station = result.scalar_one_or_none()
        if not station or not station.is_active:
            raise BusinessError(
                code="STATION_NOT_FOUND",
                message="电站不存在或已停用",
                status_code=404,
            )

        # 校验是否已有 processing 状态的导入任务（电站行已锁定，无并发竞态）
        has_processing = await self.import_job_repo.has_processing_job(station_id)
        if has_processing:
            raise BusinessError(
                code="IMPORT_ALREADY_PROCESSING",
                message="该电站已有正在运行的导入任务，请等待完成后再操作",
                status_code=409,
            )

        # 保存文件（分块流式写入，避免大文件全量加载到内存）
        job_id = uuid.uuid4()
        upload_dir = Path(settings.DATA_IMPORT_DIR) / str(job_id)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # 白名单过滤文件名：仅保留安全字符
        raw_name = Path(file.filename or "").name
        safe_name = _SAFE_FILENAME_RE.sub("_", raw_name).strip("_") if raw_name else ""
        if not safe_name:
            safe_name = "uploaded_file"
        file_path = upload_dir / safe_name

        file_size = 0
        try:
            with open(file_path, "wb") as f:
                while True:
                    chunk = await file.read(_UPLOAD_CHUNK_SIZE)
                    if not chunk:
                        break
                    file_size += len(chunk)
                    if file_size > settings.MAX_IMPORT_FILE_SIZE:
                        raise BusinessError(
                            code="FILE_TOO_LARGE",
                            message=f"文件大小超出限制，最大 {settings.MAX_IMPORT_FILE_SIZE // (1024 * 1024)}MB",
                            status_code=422,
                        )
                    f.write(chunk)
        except BusinessError:
            # 清理已写入的不完整文件
            file_path.unlink(missing_ok=True)
            upload_dir.rmdir()
            raise

        # 创建导入任务记录（失败时清理已写入的孤儿文件）
        try:
            job = DataImportJob(
                id=job_id,
                file_name=f"{job_id}/{safe_name}",
                original_file_name=file.filename or safe_name,
                file_size=file_size,
                station_id=station_id,
                imported_by=current_user.id,
            )
            created_job = await self.import_job_repo.create(job)

            # 审计日志
            await self.audit_service.log_action(
                user_id=current_user.id,
                action="create_import_job",
                resource_type="data_import_job",
                resource_id=created_job.id,
                changes_after={
                    "file_name": created_job.original_file_name,
                    "file_size": created_job.file_size,
                    "station_id": str(station_id),
                },
                ip_address=client_ip,
            )

            # 提交事务，确保 Celery worker 能看到新创建的 job
            # 注意：这里必须显式 commit，因为 Celery worker 运行在独立进程/连接中
            await self.import_job_repo.session.commit()
        except Exception:
            # DB 操作失败，清理已写入的孤儿文件
            import shutil

            shutil.rmtree(upload_dir, ignore_errors=True)
            raise

        # 触发 Celery 异步任务
        from app.tasks.import_tasks import process_trading_data_import

        try:
            task = process_trading_data_import.delay(str(created_job.id))
        except Exception as e:
            # Celery 派发失败，标记 job 为 failed
            created_job.status = "failed"
            created_job.error_message = f"任务派发失败: {str(e)[:500]}"
            await self.import_job_repo.session.commit()
            logger.error("celery_dispatch_failed", job_id=str(job_id), error=str(e))
            raise BusinessError(
                code="IMPORT_DISPATCH_FAILED",
                message="导入任务派发失败，请稍后重试",
                status_code=500,
            )

        created_job.celery_task_id = task.id
        await self.import_job_repo.session.commit()

        logger.info(
            "import_job_created",
            job_id=str(created_job.id),
            station_id=str(station_id),
            file_name=created_job.original_file_name,
            admin=current_user.username,
        )

        return created_job

    async def get_import_job(self, job_id: UUID) -> DataImportJob:
        job = await self.import_job_repo.get_by_id(job_id)
        if not job:
            raise BusinessError(
                code="IMPORT_JOB_NOT_FOUND",
                message="导入任务不存在",
                status_code=404,
            )
        return job

    async def list_import_jobs(
        self,
        page: int = 1,
        page_size: int = 20,
        station_id: UUID | None = None,
        status: str | None = None,
    ) -> tuple[list[DataImportJob], int]:
        return await self.import_job_repo.list_all_paginated(
            page=page,
            page_size=page_size,
            status_filter=status,
            station_id=station_id,
        )

    async def get_import_result(self, job_id: UUID) -> dict:
        job = await self.get_import_job(job_id)
        anomaly_summary = await self.anomaly_repo.get_summary_by_job(job_id)
        return {
            "total_records": job.total_records,
            "success_records": job.success_records,
            "failed_records": job.failed_records,
            "data_completeness": job.data_completeness,
            "anomaly_summary": anomaly_summary,
        }

    async def cancel_import_job(
        self,
        job_id: UUID,
        current_user: User,
        client_ip: str | None = None,
    ) -> DataImportJob:
        self._warn_if_no_ip("cancel_import_job", client_ip)

        job = await self.import_job_repo.get_by_id_for_update(job_id)
        if not job:
            raise BusinessError(
                code="IMPORT_JOB_NOT_FOUND",
                message="导入任务不存在",
                status_code=404,
            )

        if job.status != "processing":
            raise BusinessError(
                code="IMPORT_CANNOT_CANCEL",
                message=f"当前状态为 {job.status}，仅 processing 状态的任务可以取消",
                status_code=409,
            )

        # Revoke Celery 任务
        if job.celery_task_id:
            from app.tasks.celery_app import celery_app

            celery_app.control.revoke(job.celery_task_id, terminate=True)

        job.status = "cancelled"
        await self.import_job_repo.session.flush()

        await self.audit_service.log_action(
            user_id=current_user.id,
            action="cancel_import_job",
            resource_type="data_import_job",
            resource_id=job.id,
            changes_before={"status": "processing"},
            changes_after={"status": "cancelled"},
            ip_address=client_ip,
        )

        await self.import_job_repo.session.refresh(job)

        logger.info(
            "import_job_cancelled",
            job_id=str(job.id),
            admin=current_user.username,
        )

        return job

    async def resume_import_job(
        self,
        job_id: UUID,
        current_user: User,
        client_ip: str | None = None,
    ) -> DataImportJob:
        self._warn_if_no_ip("resume_import_job", client_ip)

        job = await self.import_job_repo.get_by_id_for_update(job_id)
        if not job:
            raise BusinessError(
                code="IMPORT_JOB_NOT_FOUND",
                message="导入任务不存在",
                status_code=404,
            )

        if job.status not in ("failed", "cancelled"):
            raise BusinessError(
                code="IMPORT_CANNOT_RESUME",
                message=f"当前状态为 {job.status}，仅 failed/cancelled 状态的任务可以恢复",
                status_code=409,
            )

        previous_status = job.status
        resume_from_row = job.last_processed_row
        job.status = "processing"
        job.error_message = None

        await self.audit_service.log_action(
            user_id=current_user.id,
            action="resume_import_job",
            resource_type="data_import_job",
            resource_id=job.id,
            changes_before={"status": previous_status},
            changes_after={"status": "processing", "resume_from_row": resume_from_row},
            ip_address=client_ip,
        )

        # 提交事务，确保 Celery worker 能看到状态变更
        await self.import_job_repo.session.commit()

        # 重新触发 Celery 任务（断点续传）
        from app.tasks.import_tasks import process_trading_data_import

        try:
            task = process_trading_data_import.delay(
                str(job.id), resume_from_row=resume_from_row,
            )
        except Exception as e:
            job.status = "failed"
            job.error_message = f"任务派发失败: {str(e)[:500]}"
            await self.import_job_repo.session.commit()
            logger.error("celery_dispatch_failed", job_id=str(job.id), error=str(e))
            raise BusinessError(
                code="IMPORT_DISPATCH_FAILED",
                message="导入任务派发失败，请稍后重试",
                status_code=500,
            )

        job.celery_task_id = task.id
        await self.import_job_repo.session.commit()

        logger.info(
            "import_job_resumed",
            job_id=str(job.id),
            resume_from_row=resume_from_row,
            admin=current_user.username,
        )

        return job

    async def get_anomalies(
        self,
        job_id: UUID,
        page: int = 1,
        page_size: int = 20,
        anomaly_type: str | None = None,
    ) -> tuple[list, int]:
        # 先验证 job 存在
        await self.get_import_job(job_id)
        return await self.anomaly_repo.list_by_job(
            job_id=job_id,
            page=page,
            page_size=page_size,
            anomaly_type_filter=anomaly_type,
        )

    async def cleanup_expired_files(
        self,
        ttl_days: int = 30,
    ) -> int:
        """清理已完成/失败且超过 TTL 的导入任务文件。

        返回清理的文件目录数。
        """
        import shutil

        cutoff = datetime.now(timezone.utc) - timedelta(days=ttl_days)
        jobs = await self.import_job_repo.list_expired_jobs(
            statuses=["completed", "failed", "cancelled"],
            before=cutoff,
        )

        cleaned = 0
        for job in jobs:
            job_dir = Path(settings.DATA_IMPORT_DIR) / str(job.id)
            if job_dir.exists():
                shutil.rmtree(job_dir, ignore_errors=True)
                cleaned += 1
                logger.info("import_file_cleaned", job_id=str(job.id))

        return cleaned
