import json
import re
import uuid
from datetime import date as date_type
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID

import structlog
from fastapi import UploadFile
from sqlalchemy import select

from app.core.config import settings
from app.core.exceptions import BusinessError
from app.models.data_import import DataImportJob, ImportAnomaly
from app.models.station import PowerStation
from app.models.user import User
from app.repositories.data_import import (
    DataImportJobRepository,
    ImportAnomalyRepository,
    StationOutputRepository,
    StorageOperationRepository,
    TradingRecordRepository,
)
from app.repositories.station import StationRepository
from app.repositories.storage import StorageDeviceRepository
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
        station_output_repo: StationOutputRepository | None = None,
        storage_operation_repo: StorageOperationRepository | None = None,
        storage_device_repo: StorageDeviceRepository | None = None,
    ):
        self.import_job_repo = import_job_repo
        self.trading_record_repo = trading_record_repo
        self.anomaly_repo = anomaly_repo
        self.station_repo = station_repo
        self.audit_service = audit_service
        self.station_output_repo = station_output_repo
        self.storage_operation_repo = storage_operation_repo
        self.storage_device_repo = storage_device_repo

    def _warn_if_no_ip(self, action: str, ip_address: str | None) -> None:
        if ip_address is None:
            logger.warning("audit_ip_missing", action=action, hint="非 HTTP 上下文调用，IP 地址缺失")

    async def create_import_job(
        self,
        station_id: UUID,
        file: UploadFile,
        current_user: User,
        client_ip: str | None = None,
        import_type: str = "trading_data",
        ems_format: str | None = None,
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
                import_type=import_type,
                ems_format=ems_format if import_type == "storage_operation" else None,
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
                    "import_type": import_type,
                    "ems_format": ems_format,
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

        # 触发 Celery 异步任务（根据 import_type 选择对应任务）
        from app.tasks.import_tasks import (
            process_station_output_import,
            process_storage_operation_import,
            process_trading_data_import,
        )

        task_map = {
            "trading_data": process_trading_data_import,
            "station_output": process_station_output_import,
            "storage_operation": process_storage_operation_import,
        }
        celery_task = task_map[import_type]

        try:
            task_kwargs = {"job_id": str(created_job.id)}
            if import_type == "storage_operation" and ems_format:
                task_kwargs["ems_format"] = ems_format
            task = celery_task.apply_async(kwargs=task_kwargs)
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
        import_type: str | None = None,
    ) -> tuple[list[DataImportJob], int]:
        return await self.import_job_repo.list_all_paginated(
            page=page,
            page_size=page_size,
            status_filter=status,
            station_id=station_id,
            import_type_filter=import_type,
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

    async def list_output_records(
        self,
        job_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list, int]:
        job = await self.get_import_job(job_id)
        if job.import_type != "station_output":
            raise BusinessError(
                code="INVALID_IMPORT_TYPE",
                message="该任务不是电站出力数据导入",
                status_code=400,
            )
        return await self.station_output_repo.list_by_job(
            import_job_id=job_id, page=page, page_size=page_size,
        )

    async def list_storage_records(
        self,
        job_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list, int]:
        job = await self.get_import_job(job_id)
        if job.import_type != "storage_operation":
            raise BusinessError(
                code="INVALID_IMPORT_TYPE",
                message="该任务不是储能运行数据导入",
                status_code=400,
            )
        return await self.storage_operation_repo.list_by_job(
            import_job_id=job_id, page=page, page_size=page_size,
        )

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

        # 重新触发 Celery 任务（断点续传，根据 import_type 选择）
        from app.tasks.import_tasks import (
            process_station_output_import,
            process_storage_operation_import,
            process_trading_data_import,
        )

        task_map = {
            "trading_data": process_trading_data_import,
            "station_output": process_station_output_import,
            "storage_operation": process_storage_operation_import,
        }
        if job.import_type not in task_map:
            raise BusinessError(
                code="INVALID_IMPORT_TYPE",
                message=f"不支持的导入类型: {job.import_type}",
                status_code=400,
            )
        celery_task = task_map[job.import_type]

        try:
            task_kwargs: dict = {"job_id": str(job.id), "resume_from_row": resume_from_row}
            if job.import_type == "storage_operation" and job.ems_format:
                task_kwargs["ems_format"] = job.ems_format
            task = celery_task.apply_async(
                kwargs=task_kwargs,
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

    # --- 异常管理 (Story 2.4) ---

    async def _get_anomaly_or_raise(self, anomaly_id: UUID) -> ImportAnomaly:
        anomaly = await self.anomaly_repo.get_by_id(anomaly_id)
        if not anomaly:
            raise BusinessError(
                code="ANOMALY_NOT_FOUND",
                message="异常记录不存在",
                status_code=404,
            )
        return anomaly

    async def _check_anomaly_pending(self, anomaly: ImportAnomaly) -> None:
        if anomaly.status != "pending":
            raise BusinessError(
                code="ANOMALY_ALREADY_PROCESSED",
                message=f"该异常已处理（当前状态: {anomaly.status}），不可再次操作",
                status_code=409,
            )

    # 各导入类型支持的修正字段
    _CORRECTABLE_FIELDS: dict[str, set[str]] = {
        "trading_data": {"clearing_price", "period", "trading_date"},
        "station_output": {"actual_output_kw", "period", "trading_date"},
        "storage_operation": {"soc", "charge_power_kw", "discharge_power_kw",
                              "cycle_count", "period", "trading_date"},
    }

    def _validate_corrected_value(
        self, field_name: str, corrected_value: str, anomaly_type: str,
        import_type: str = "trading_data",
    ) -> dict:
        """校验修正值并返回解析后的数据字段字典。"""
        # 尝试 JSON 多字段修正
        try:
            parsed = json.loads(corrected_value)
            if isinstance(parsed, dict):
                return self._validate_multi_field(parsed, import_type)
        except (json.JSONDecodeError, ValueError):
            pass

        allowed = self._CORRECTABLE_FIELDS.get(import_type, set())
        if field_name not in allowed:
            raise BusinessError(
                code="INVALID_CORRECTED_VALUE",
                message=f"导入类型 {import_type} 不支持修正字段: {field_name}",
                status_code=422,
            )

        # 公共字段
        if field_name == "period":
            return self._validate_period(corrected_value)
        elif field_name == "trading_date":
            return self._validate_trading_date(corrected_value)
        # trading_data 字段
        elif field_name == "clearing_price":
            return self._validate_price(corrected_value)
        # station_output 字段
        elif field_name == "actual_output_kw":
            return self._validate_output_kw(corrected_value)
        # storage_operation 字段
        elif field_name == "soc":
            return self._validate_soc(corrected_value)
        elif field_name in ("charge_power_kw", "discharge_power_kw"):
            return self._validate_power_kw(field_name, corrected_value)
        elif field_name == "cycle_count":
            return self._validate_cycle_count(corrected_value)
        else:
            raise BusinessError(
                code="INVALID_CORRECTED_VALUE",
                message=f"不支持的修正字段: {field_name}",
                status_code=422,
            )

    def _validate_price(self, value: str) -> dict:
        try:
            price = Decimal(value)
        except InvalidOperation:
            raise BusinessError(
                code="INVALID_CORRECTED_VALUE",
                message=f"出清价格格式错误: {value}，请输入有效的数值",
                status_code=422,
            )
        if price != price or not price.is_finite():  # NaN or Inf check
            raise BusinessError(
                code="INVALID_CORRECTED_VALUE",
                message="出清价格不能为 NaN 或 Infinity",
                status_code=422,
            )
        return {"clearing_price": price}

    def _validate_period(self, value: str) -> dict:
        try:
            period = int(value)
        except ValueError:
            raise BusinessError(
                code="INVALID_CORRECTED_VALUE",
                message=f"时段格式错误: {value}，请输入 1-96 的整数",
                status_code=422,
            )
        if period < 1 or period > 96:
            raise BusinessError(
                code="INVALID_CORRECTED_VALUE",
                message=f"时段超出范围: {period}，有效范围为 1-96",
                status_code=422,
            )
        return {"period": period}

    def _validate_trading_date(self, value: str) -> dict:
        try:
            parsed_date = date_type.fromisoformat(value)
        except ValueError:
            raise BusinessError(
                code="INVALID_CORRECTED_VALUE",
                message=f"交易日期格式错误: {value}，请使用 YYYY-MM-DD 格式",
                status_code=422,
            )
        return {"trading_date": parsed_date}

    def _validate_output_kw(self, value: str) -> dict:
        try:
            kw = Decimal(value)
        except InvalidOperation:
            raise BusinessError(
                code="INVALID_CORRECTED_VALUE",
                message=f"实际出力格式错误: {value}，请输入有效的数值",
                status_code=422,
            )
        if kw < 0:
            raise BusinessError(
                code="INVALID_CORRECTED_VALUE",
                message=f"实际出力不能为负数: {value}",
                status_code=422,
            )
        return {"actual_output_kw": kw}

    def _validate_soc(self, value: str) -> dict:
        try:
            soc = Decimal(value)
        except InvalidOperation:
            raise BusinessError(
                code="INVALID_CORRECTED_VALUE",
                message=f"SOC 格式错误: {value}，请输入 0.0-1.0 的数值",
                status_code=422,
            )
        if soc < 0 or soc > 1:
            raise BusinessError(
                code="INVALID_CORRECTED_VALUE",
                message=f"SOC 超出范围: {value}，有效范围为 0.0-1.0",
                status_code=422,
            )
        return {"soc": soc}

    def _validate_power_kw(self, field_name: str, value: str) -> dict:
        try:
            power = Decimal(value)
        except InvalidOperation:
            raise BusinessError(
                code="INVALID_CORRECTED_VALUE",
                message=f"功率格式错误: {value}，请输入有效的数值",
                status_code=422,
            )
        if power < 0:
            raise BusinessError(
                code="INVALID_CORRECTED_VALUE",
                message=f"功率不能为负数: {value}",
                status_code=422,
            )
        return {field_name: power}

    def _validate_cycle_count(self, value: str) -> dict:
        try:
            count = int(value)
        except ValueError:
            raise BusinessError(
                code="INVALID_CORRECTED_VALUE",
                message=f"循环次数格式错误: {value}，请输入非负整数",
                status_code=422,
            )
        if count < 0:
            raise BusinessError(
                code="INVALID_CORRECTED_VALUE",
                message=f"循环次数不能为负数: {value}",
                status_code=422,
            )
        return {"cycle_count": count}

    def _validate_multi_field(self, data: dict, import_type: str = "trading_data") -> dict:
        result = {}
        # 公共字段
        if "period" in data:
            result.update(self._validate_period(str(data["period"])))
        if "trading_date" in data:
            result.update(self._validate_trading_date(str(data["trading_date"])))
        # trading_data 字段
        if "clearing_price" in data:
            result.update(self._validate_price(str(data["clearing_price"])))
        # station_output 字段
        if "actual_output_kw" in data:
            result.update(self._validate_output_kw(str(data["actual_output_kw"])))
        # storage_operation 字段
        if "soc" in data:
            result.update(self._validate_soc(str(data["soc"])))
        if "charge_power_kw" in data:
            result.update(self._validate_power_kw("charge_power_kw", str(data["charge_power_kw"])))
        if "discharge_power_kw" in data:
            result.update(self._validate_power_kw("discharge_power_kw", str(data["discharge_power_kw"])))
        if "cycle_count" in data:
            result.update(self._validate_cycle_count(str(data["cycle_count"])))
        if not result:
            raise BusinessError(
                code="INVALID_CORRECTED_VALUE",
                message="修正值 JSON 中没有可识别的字段",
                status_code=422,
            )
        return result

    async def get_anomaly(self, anomaly_id: UUID) -> ImportAnomaly:
        return await self._get_anomaly_or_raise(anomaly_id)

    async def get_anomaly_detail(self, anomaly_id: UUID) -> dict:
        """获取异常详情，关联 import_job 的文件名和电站信息。"""
        anomaly = await self._get_anomaly_or_raise(anomaly_id)
        job = await self.import_job_repo.get_by_id(anomaly.import_job_id)
        return {
            "anomaly": anomaly,
            "original_file_name": job.original_file_name if job else None,
            "station_id": job.station_id if job else None,
        }

    async def get_anomaly_summary(
        self,
        import_job_id: UUID | None = None,
        status: str | None = None,
    ) -> list[dict]:
        """获取异常分类统计。"""
        return await self.anomaly_repo.get_summary_all(
            import_job_id_filter=import_job_id,
            status_filter=status,
        )

    async def _write_correction(
        self,
        job: DataImportJob,
        validated_fields: dict,
        anomaly_id: UUID,
    ) -> None:
        """根据 import_type 将修正值写入对应的数据表。"""
        import_type = job.import_type

        if import_type == "trading_data":
            record = {"station_id": job.station_id, "import_job_id": job.id}
            for k in ("trading_date", "period", "clearing_price"):
                if k in validated_fields:
                    record[k] = validated_fields[k]
            if all(k in record for k in ["trading_date", "period", "clearing_price"]):
                await self.trading_record_repo.upsert_record(record)
            else:
                logger.info("correction_write_skipped", anomaly_id=str(anomaly_id),
                            reason="单字段修正缺少完整行上下文")

        elif import_type == "station_output":
            record = {"station_id": job.station_id, "import_job_id": job.id}
            for k in ("trading_date", "period", "actual_output_kw"):
                if k in validated_fields:
                    record[k] = validated_fields[k]
            if all(k in record for k in ["trading_date", "period", "actual_output_kw"]):
                await self.station_output_repo.upsert_record(record)
            else:
                logger.info("correction_write_skipped", anomaly_id=str(anomaly_id),
                            reason="单字段修正缺少完整行上下文")

        elif import_type == "storage_operation":
            # storage_operation 需要 device_id，此处暂不支持单字段写入
            # （需要设备上下文），仅更新异常状态
            logger.info("correction_write_skipped", anomaly_id=str(anomaly_id),
                        reason="storage_operation 修正仅更新异常状态")

    async def correct_anomaly(
        self,
        anomaly_id: UUID,
        corrected_value: str,
        current_user: User,
        client_ip: str | None = None,
    ) -> ImportAnomaly:
        self._warn_if_no_ip("correct_anomaly", client_ip)

        anomaly = await self.anomaly_repo.get_by_id_for_update(anomaly_id)
        if not anomaly:
            raise BusinessError(
                code="ANOMALY_NOT_FOUND",
                message="异常记录不存在",
                status_code=404,
            )
        await self._check_anomaly_pending(anomaly)

        # 校验修正值（根据 import_type 支持不同字段）
        job = await self.import_job_repo.get_by_id(anomaly.import_job_id)
        import_type = job.import_type if job else "trading_data"
        validated_fields = self._validate_corrected_value(
            anomaly.field_name, corrected_value, anomaly.anomaly_type,
            import_type=import_type,
        )

        # 修正值写入对应数据表（duplicate 类型不写入）
        if anomaly.anomaly_type != "duplicate" and job:
            await self._write_correction(job, validated_fields, anomaly_id)

        # 无论是否写入 trading_records，修正即代表异常已解决，更新 job 计数
        if job:
            job.success_records += 1
            job.failed_records = max(0, job.failed_records - 1)
            if job.total_records > 0:
                job.data_completeness = Decimal(
                    str(round(job.success_records / job.total_records * 100, 2)),
                )
            await self.import_job_repo.session.flush()

        # 更新异常状态（保留 raw_value 原始值，修正值记录在审计日志中）
        old_value = anomaly.raw_value
        await self.anomaly_repo.update_anomaly_status(anomaly_id, "corrected")

        # 审计日志
        await self.audit_service.log_action(
            user_id=current_user.id,
            action="correct_anomaly",
            resource_type="import_anomaly",
            resource_id=anomaly_id,
            changes_before={
                "raw_value": old_value,
                "status": "pending",
            },
            changes_after={
                "corrected_value": corrected_value,
                "status": "corrected",
            },
            ip_address=client_ip,
        )

        logger.info(
            "anomaly_corrected",
            anomaly_id=str(anomaly_id),
            admin=current_user.username,
        )

        # 刷新获取最新状态
        anomaly = await self.anomaly_repo.get_by_id(anomaly_id)
        return anomaly

    async def confirm_anomaly_normal(
        self,
        anomaly_id: UUID,
        current_user: User,
        client_ip: str | None = None,
    ) -> ImportAnomaly:
        self._warn_if_no_ip("confirm_anomaly_normal", client_ip)

        anomaly = await self.anomaly_repo.get_by_id_for_update(anomaly_id)
        if not anomaly:
            raise BusinessError(
                code="ANOMALY_NOT_FOUND",
                message="异常记录不存在",
                status_code=404,
            )
        await self._check_anomaly_pending(anomaly)

        await self.anomaly_repo.update_anomaly_status(anomaly_id, "confirmed_normal")

        await self.audit_service.log_action(
            user_id=current_user.id,
            action="confirm_anomaly_normal",
            resource_type="import_anomaly",
            resource_id=anomaly_id,
            changes_before={"status": "pending"},
            changes_after={"status": "confirmed_normal"},
            ip_address=client_ip,
        )

        logger.info(
            "anomaly_confirmed_normal",
            anomaly_id=str(anomaly_id),
            admin=current_user.username,
        )

        anomaly = await self.anomaly_repo.get_by_id(anomaly_id)
        return anomaly

    async def _validate_bulk_pending(self, anomaly_ids: list[UUID]) -> list[ImportAnomaly]:
        """批量校验异常 ID 存在且为 pending 状态，返回异常记录列表。"""
        anomalies = await self.anomaly_repo.get_by_ids(anomaly_ids)
        found_ids = {a.id for a in anomalies}
        missing = set(anomaly_ids) - found_ids
        if missing:
            raise BusinessError(
                code="ANOMALY_NOT_FOUND",
                message=f"异常记录不存在: {', '.join(str(m) for m in missing)}",
                status_code=404,
            )
        non_pending = [a for a in anomalies if a.status != "pending"]
        if non_pending:
            aid = non_pending[0].id
            raise BusinessError(
                code="BULK_PARTIAL_FAILURE",
                message=f"异常 {aid} 已处理（状态: {non_pending[0].status}），不可批量操作",
                status_code=409,
            )
        return anomalies

    async def bulk_delete_anomalies(
        self,
        anomaly_ids: list[UUID],
        current_user: User,
        client_ip: str | None = None,
    ) -> int:
        self._warn_if_no_ip("bulk_delete_anomalies", client_ip)

        await self._validate_bulk_pending(anomaly_ids)

        affected = await self.anomaly_repo.bulk_update_status(anomaly_ids, "deleted")

        await self.audit_service.log_action(
            user_id=current_user.id,
            action="bulk_delete_anomalies",
            resource_type="import_anomaly",
            resource_id=anomaly_ids[0],
            changes_after={
                "action": "bulk_delete",
                "affected_count": affected,
                "anomaly_ids": [str(aid) for aid in anomaly_ids],
            },
            ip_address=client_ip,
        )

        logger.info(
            "anomalies_bulk_deleted",
            count=affected,
            admin=current_user.username,
        )

        return affected

    async def bulk_confirm_normal(
        self,
        anomaly_ids: list[UUID],
        current_user: User,
        client_ip: str | None = None,
    ) -> int:
        self._warn_if_no_ip("bulk_confirm_normal", client_ip)

        await self._validate_bulk_pending(anomaly_ids)

        affected = await self.anomaly_repo.bulk_update_status(anomaly_ids, "confirmed_normal")

        await self.audit_service.log_action(
            user_id=current_user.id,
            action="bulk_confirm_normal",
            resource_type="import_anomaly",
            resource_id=anomaly_ids[0],
            changes_after={
                "action": "bulk_confirm_normal",
                "affected_count": affected,
                "anomaly_ids": [str(aid) for aid in anomaly_ids],
            },
            ip_address=client_ip,
        )

        logger.info(
            "anomalies_bulk_confirmed_normal",
            count=affected,
            admin=current_user.username,
        )

        return affected

    async def list_anomalies_global(
        self,
        page: int = 1,
        page_size: int = 20,
        anomaly_type: str | None = None,
        status: str | None = None,
        import_job_id: UUID | None = None,
    ) -> tuple[list, int]:
        return await self.anomaly_repo.list_all_anomalies(
            page=page,
            page_size=page_size,
            anomaly_type_filter=anomaly_type,
            status_filter=status,
            import_job_id_filter=import_job_id,
        )
