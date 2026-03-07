import time
from datetime import UTC, date, datetime
from uuid import UUID

import structlog

from app.core.exceptions import BusinessError
from app.core.prediction_encryption import decrypt_api_key, encrypt_api_key
from app.models.prediction import PredictionModel
from app.repositories.prediction import PowerPredictionRepository, PredictionModelRepository
from app.schemas.prediction import ConnectionTestResult, FetchResult, PredictionModelStatus
from app.services.audit_service import AuditService
from app.services.prediction_adapters import get_adapter
from app.services.prediction_adapters.base import PredictionRecord

logger = structlog.get_logger()

# M4 fix: 保留旧别名以兼容外部 import（prediction_tasks.py 等）
_encrypt_api_key = encrypt_api_key
_decrypt_api_key = decrypt_api_key


def validate_prediction_records(
    records: list[PredictionRecord],
) -> tuple[list[PredictionRecord], list[str]]:
    """校验预测记录数据质量，返回 (有效记录, 错误信息列表)。"""
    valid, errors = [], []
    for r in records:
        if not (1 <= r.period <= 96):
            errors.append(f"Invalid period {r.period}")
            continue
        if r.predicted_power_kw < 0:
            errors.append(f"Period {r.period}: negative power {r.predicted_power_kw}")
            continue
        if not (r.confidence_lower_kw <= r.predicted_power_kw <= r.confidence_upper_kw):
            errors.append(f"Period {r.period}: confidence violation")
            continue
        valid.append(r)
    if len(valid) < 96:
        errors.append(f"Incomplete: {len(valid)}/96 valid records")
    return valid, errors


class PredictionService:
    def __init__(
        self,
        model_repo: PredictionModelRepository,
        audit_service: AuditService,
        prediction_repo: PowerPredictionRepository | None = None,
    ):
        self.model_repo = model_repo
        self.audit_service = audit_service
        self.prediction_repo = prediction_repo

    # --- CRUD ---

    async def create_model(
        self,
        model_name: str,
        model_type: str,
        api_endpoint: str,
        api_key: str | None,
        api_auth_type: str,
        call_frequency_cron: str,
        timeout_seconds: int,
        station_id: UUID,
        user_id: UUID | None = None,
    ) -> PredictionModel:
        model = PredictionModel(
            station_id=station_id,
            model_name=model_name,
            model_type=model_type,
            api_endpoint=api_endpoint,
            api_key_encrypted=_encrypt_api_key(api_key) if api_key else None,
            api_auth_type=api_auth_type,
            call_frequency_cron=call_frequency_cron,
            timeout_seconds=timeout_seconds,
        )
        created = await self.model_repo.create(model)

        if user_id:
            await self.audit_service.log_action(
                user_id=user_id,
                action="create_prediction_model",
                resource_type="prediction_model",
                resource_id=created.id,
                changes_after={
                    "model_name": model_name,
                    "station_id": str(station_id),
                    "model_type": model_type,
                },
            )

        # 自动执行一次连接测试
        test_result = await self.test_connection(created.id)
        # test_connection 内部已通过 update_check_result 更新了 DB 状态
        # 刷新 ORM 对象以反映最新的 DB 状态
        await self.model_repo.session.refresh(created)

        logger.info(
            "prediction_model_created",
            model_id=str(created.id),
            model_name=model_name,
            station_id=str(station_id),
        )
        return created

    async def update_model(
        self,
        model_id: UUID,
        update_data: dict,
        user_id: UUID | None = None,
    ) -> PredictionModel:
        model = await self.model_repo.get_by_id(model_id)
        if not model:
            raise BusinessError(
                code="MODEL_NOT_FOUND",
                message="预测模型不存在",
                status_code=404,
            )

        # 记录被修改字段的旧值（用于审计）
        before = {}
        for key in update_data:
            if key == "api_key":
                before["api_key"] = "***已存在***" if model.api_key_encrypted else None
            elif hasattr(model, key):
                before[key] = getattr(model, key)

        api_key_changed = False
        if "api_key" in update_data:
            api_key = update_data.pop("api_key")
            if api_key:
                model.api_key_encrypted = _encrypt_api_key(api_key)
                api_key_changed = True
            else:
                model.api_key_encrypted = None
                api_key_changed = True

        for key, value in update_data.items():
            if value is not None and hasattr(model, key):
                setattr(model, key, value)

        await self.model_repo.session.flush()
        await self.model_repo.session.refresh(model)

        if user_id:
            audit_changes = dict(update_data)
            if api_key_changed:
                audit_changes["api_key"] = "***已变更***"
            await self.audit_service.log_action(
                user_id=user_id,
                action="update_prediction_model",
                resource_type="prediction_model",
                resource_id=model_id,
                changes_before=before,
                changes_after=audit_changes,
            )

        logger.info(
            "prediction_model_updated",
            model_id=str(model_id),
        )
        return model

    async def delete_model(
        self,
        model_id: UUID,
        user_id: UUID | None = None,
    ) -> None:
        model = await self.model_repo.get_by_id(model_id)
        if not model:
            raise BusinessError(
                code="MODEL_NOT_FOUND",
                message="预测模型不存在",
                status_code=404,
            )

        if user_id:
            await self.audit_service.log_action(
                user_id=user_id,
                action="delete_prediction_model",
                resource_type="prediction_model",
                resource_id=model_id,
                changes_before={"model_name": model.model_name},
            )

        await self.model_repo.delete(model)
        logger.info("prediction_model_deleted", model_id=str(model_id))

    async def get_model(self, model_id: UUID) -> PredictionModel:
        model = await self.model_repo.get_by_id(model_id)
        if not model:
            raise BusinessError(
                code="MODEL_NOT_FOUND",
                message="预测模型不存在",
                status_code=404,
            )
        return model

    async def list_models(
        self,
        station_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PredictionModel], int]:
        return await self.model_repo.list_all_paginated(
            station_id=station_id,
            page=page,
            page_size=page_size,
        )

    # --- 连接测试 ---

    async def test_connection(self, model_id: UUID) -> ConnectionTestResult:
        model = await self.model_repo.get_by_id(model_id)
        if not model:
            raise BusinessError(
                code="MODEL_NOT_FOUND",
                message="预测模型不存在",
                status_code=404,
            )

        api_key = None
        if model.api_key_encrypted:
            api_key = _decrypt_api_key(model.api_key_encrypted)

        adapter = get_adapter(model, api_key=api_key)
        now = datetime.now(UTC)

        start = time.monotonic()
        try:
            is_healthy = await adapter.health_check()
            elapsed_ms = (time.monotonic() - start) * 1000

            if is_healthy:
                await self.model_repo.update_check_result(
                    model_id,
                    status="running",
                    check_status="success",
                    check_at=now,
                )
                return ConnectionTestResult(
                    success=True,
                    latency_ms=round(elapsed_ms, 1),
                    tested_at=now,
                )
            else:
                await self.model_repo.update_check_result(
                    model_id,
                    status="error",
                    check_status="failed",
                    error="API 返回错误状态",
                    check_at=now,
                )
                return ConnectionTestResult(
                    success=False,
                    latency_ms=round(elapsed_ms, 1),
                    error_message="API 返回错误状态",
                    tested_at=now,
                )
        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            error_msg = str(e)[:500]
            await self.model_repo.update_check_result(
                model_id,
                status="error",
                check_status="failed",
                error=error_msg,
                check_at=now,
            )
            return ConnectionTestResult(
                success=False,
                latency_ms=round(elapsed_ms, 1),
                error_message=error_msg,
                tested_at=now,
            )

    # --- 健康检查 ---

    async def check_model_health(self, model_id: UUID) -> str:
        """检查单个模型健康状态，返回新状态。"""
        model = await self.model_repo.get_by_id(model_id)
        if not model:
            return "error"

        api_key = None
        if model.api_key_encrypted:
            api_key = _decrypt_api_key(model.api_key_encrypted)

        adapter = get_adapter(model, api_key=api_key)
        now = datetime.now(UTC)

        try:
            is_healthy = await adapter.health_check()
            new_status = "running" if is_healthy else "error"
            check_status = "success" if is_healthy else "failed"
            error = None if is_healthy else "健康检查失败"

            await self.model_repo.update_check_result(
                model_id,
                status=new_status,
                check_status=check_status,
                error=error,
                check_at=now,
            )
            return new_status
        except Exception as e:
            error_msg = str(e)[:500]
            await self.model_repo.update_check_result(
                model_id,
                status="error",
                check_status="failed",
                error=error_msg,
                check_at=now,
            )
            logger.warning(
                "prediction_model_health_check_failed",
                model_id=str(model_id),
                error=error_msg,
            )
            return "error"

    # --- 数据拉取 ---

    async def fetch_predictions(
        self,
        model_id: UUID,
        prediction_date: date,
        user_id: UUID | None = None,
    ) -> FetchResult:
        """拉取指定模型的预测数据并写入数据库。"""
        model = await self.model_repo.get_by_id(model_id)
        if not model:
            raise BusinessError(
                code="MODEL_NOT_FOUND",
                message="预测模型不存在",
                status_code=404,
            )

        if not self.prediction_repo:
            raise BusinessError(
                code="SERVICE_ERROR",
                message="预测数据仓库未初始化",
                status_code=500,
            )

        now = datetime.now(UTC)

        # M1 fix: 使用针对性查询获取电站名称（替代全量查询）
        station_name = await self.model_repo.get_station_name_by_model_id(model_id)

        try:
            api_key = None
            if model.api_key_encrypted:
                api_key = _decrypt_api_key(model.api_key_encrypted)

            adapter = get_adapter(model, api_key=api_key)
            records = await adapter.fetch_predictions(
                str(model.station_id), prediction_date,
            )

            # 数据质量校验
            valid_records, quality_errors = validate_prediction_records(records)

            if not valid_records:
                # 全部无效
                error_msg = "; ".join(quality_errors[:5])
                await self.model_repo.update_fetch_result(
                    model_id, status="failed", error=error_msg, fetch_at=now,
                )
                if user_id:
                    await self.audit_service.log_action(
                        user_id=user_id,
                        action="fetch_prediction_data",
                        resource_type="prediction_model",
                        resource_id=model_id,
                        changes_after={"status": "failed", "error": error_msg},
                    )
                logger.warning(
                    "prediction_fetch_quality_failed",
                    model_id=str(model_id),
                    errors=quality_errors,
                )
                return FetchResult(
                    model_id=model.id,
                    model_name=model.model_name,
                    station_name=station_name,
                    success=False,
                    records_count=0,
                    error_message=error_msg,
                    fetched_at=now,
                )

            # 写入有效数据
            record_dicts = [
                {
                    "prediction_date": prediction_date,
                    "period": r.period,
                    "station_id": model.station_id,
                    "model_id": model.id,
                    "predicted_power_kw": r.predicted_power_kw,
                    "confidence_upper_kw": r.confidence_upper_kw,
                    "confidence_lower_kw": r.confidence_lower_kw,
                    "source": "api",
                }
                for r in valid_records
            ]
            count = await self.prediction_repo.bulk_upsert(record_dicts)

            # 确定状态
            fetch_status = "success" if len(valid_records) == 96 else "partial"
            error_msg = None
            if quality_errors:
                error_msg = "; ".join(quality_errors[:5])

            await self.model_repo.update_fetch_result(
                model_id, status=fetch_status, error=error_msg, fetch_at=now,
            )

            if user_id:
                await self.audit_service.log_action(
                    user_id=user_id,
                    action="fetch_prediction_data",
                    resource_type="prediction_model",
                    resource_id=model_id,
                    changes_after={
                        "status": fetch_status,
                        "records_count": count,
                        "prediction_date": prediction_date.isoformat(),
                    },
                )

            logger.info(
                "prediction_fetch_success",
                model_id=str(model_id),
                records_count=count,
                fetch_status=fetch_status,
                prediction_date=prediction_date.isoformat(),
            )

            return FetchResult(
                model_id=model.id,
                model_name=model.model_name,
                station_name=station_name,
                success=True,
                records_count=count,
                error_message=error_msg,
                fetched_at=now,
            )

        except Exception as e:
            error_msg = str(e)[:500]
            await self.model_repo.update_fetch_result(
                model_id, status="failed", error=error_msg, fetch_at=now,
            )

            if user_id:
                await self.audit_service.log_action(
                    user_id=user_id,
                    action="fetch_prediction_data",
                    resource_type="prediction_model",
                    resource_id=model_id,
                    changes_after={"status": "failed", "error": error_msg},
                )

            logger.warning(
                "prediction_fetch_failed",
                model_id=str(model_id),
                error=error_msg,
            )
            return FetchResult(
                model_id=model.id,
                model_name=model.model_name,
                station_name=station_name,
                success=False,
                records_count=0,
                error_message=error_msg,
                fetched_at=now,
            )

    async def get_all_model_statuses(self) -> list[PredictionModelStatus]:
        """获取所有模型运行状态概览（含电站名称）。"""
        rows = await self.model_repo.get_all_active_with_station_name()
        statuses = []
        for model, station_name in rows:
            statuses.append(
                PredictionModelStatus(
                    model_id=model.id,
                    model_name=model.model_name,
                    station_name=station_name,
                    status=model.status,
                    last_check_at=model.last_check_at,
                    last_check_error=model.last_check_error,
                    last_fetch_at=model.last_fetch_at,
                    last_fetch_status=model.last_fetch_status,
                    last_fetch_error=model.last_fetch_error,
                )
            )
        return statuses
