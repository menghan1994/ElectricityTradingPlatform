import asyncio
from datetime import UTC, date, datetime, timedelta

import structlog
from sqlalchemy import select, update

from app.core.database import get_sync_session_factory
from app.models.prediction import PredictionModel
from app.repositories.prediction import build_prediction_upsert_stmt
from app.core.prediction_encryption import decrypt_api_key
from app.services.prediction_adapters import get_adapter
from app.services.prediction_service import validate_prediction_records
from app.tasks.celery_app import celery_app

logger = structlog.get_logger()


async def _check_single_model_health(adapter) -> bool:
    """执行单个模型健康检查（在共享事件循环中运行）。"""
    return await adapter.health_check()


@celery_app.task(name="app.tasks.prediction_tasks.check_prediction_models_health")
def check_prediction_models_health() -> dict:
    """Celery beat 定时任务：每5分钟检查所有活跃预测模型的健康状态。

    状态机：running ↔ error，disabled 需管理员手动切换。
    """
    session_factory = get_sync_session_factory()
    results: dict[str, str] = {}

    with session_factory() as session:
        session.expire_on_commit = False

        stmt = select(PredictionModel).where(
            PredictionModel.is_active.is_(True),
            PredictionModel.status.in_(["running", "error"]),
        )
        models = list(session.execute(stmt).scalars().all())

        if not models:
            logger.info("prediction_health_check_no_active_models")
            return {"status": "no_active_models"}

        # 准备所有适配器
        adapters: list[tuple[PredictionModel, object]] = []
        for model in models:
            api_key = None
            if model.api_key_encrypted:
                api_key = decrypt_api_key(model.api_key_encrypted)
            adapter = get_adapter(model, api_key=api_key)
            adapters.append((model, adapter))

        # 单次 asyncio.run 批量执行所有健康检查
        async def _batch_health_check():
            return await asyncio.gather(
                *[_check_single_model_health(a) for _, a in adapters],
                return_exceptions=True,
            )

        health_results = asyncio.run(_batch_health_check())

        for (model, _adapter), health_result in zip(adapters, health_results):
            model_id = str(model.id)
            try:
                if isinstance(health_result, Exception):
                    raise health_result

                is_healthy = health_result
                now = datetime.now(UTC)

                old_status = model.status
                new_status = "running" if is_healthy else "error"
                session.execute(
                    update(PredictionModel)
                    .where(PredictionModel.id == model.id)
                    .values(
                        status=new_status,
                        last_check_at=now,
                        last_check_status="success" if is_healthy else "failed",
                        last_check_error=None if is_healthy else "健康检查失败",
                    )
                )
                session.commit()

                # 状态变更为 error 时发出 WARNING 告警
                if new_status == "error" and old_status != "error":
                    logger.warning(
                        "prediction_model_status_changed_to_error",
                        model_id=model_id,
                        model_name=model.model_name,
                        previous_status=old_status,
                    )

                results[model_id] = new_status
                logger.info(
                    "prediction_health_check_result",
                    model_id=model_id,
                    model_name=model.model_name,
                    status=new_status,
                )

            except Exception as e:
                session.rollback()
                error_msg = str(e)[:500]
                try:
                    session.execute(
                        update(PredictionModel)
                        .where(PredictionModel.id == model.id)
                        .values(
                            status="error",
                            last_check_at=datetime.now(UTC),
                            last_check_status="failed",
                            last_check_error=error_msg,
                        )
                    )
                    session.commit()
                except Exception:
                    session.rollback()

                results[model_id] = f"error:{error_msg}"
                logger.warning(
                    "prediction_health_check_exception",
                    model_id=model_id,
                    model_name=model.model_name,
                    error=error_msg,
                )

    return results


@celery_app.task(name="app.tasks.prediction_tasks.fetch_prediction_data_for_all_models")
def fetch_prediction_data_for_all_models() -> dict:
    """每日自动拉取所有 running 模型的预测数据（T+1日）。"""
    session_factory = get_sync_session_factory()
    results: dict[str, str] = {}
    prediction_date = date.today() + timedelta(days=1)

    with session_factory() as session:
        session.expire_on_commit = False

        stmt = select(PredictionModel).where(
            PredictionModel.is_active.is_(True),
            PredictionModel.status == "running",
        )
        models = list(session.execute(stmt).scalars().all())

        if not models:
            logger.info("prediction_fetch_no_running_models")
            return {"status": "no_running_models"}

        # 准备适配器
        adapters: list[tuple[PredictionModel, object]] = []
        for model in models:
            api_key = None
            if model.api_key_encrypted:
                api_key = decrypt_api_key(model.api_key_encrypted)
            adapter = get_adapter(model, api_key=api_key)
            adapters.append((model, adapter))

        # 批量并发拉取
        async def _batch_fetch():
            return await asyncio.gather(
                *[
                    adapter.fetch_predictions(str(model.station_id), prediction_date)
                    for model, adapter in adapters
                ],
                return_exceptions=True,
            )

        fetch_results = asyncio.run(_batch_fetch())

        for (model, _adapter), fetch_result in zip(adapters, fetch_results):
            model_id = str(model.id)
            now = datetime.now(UTC)

            try:
                if isinstance(fetch_result, Exception):
                    raise fetch_result

                records = fetch_result
                valid_records, quality_errors = validate_prediction_records(records)

                if not valid_records:
                    error_msg = "; ".join(quality_errors[:5])
                    session.execute(
                        update(PredictionModel)
                        .where(PredictionModel.id == model.id)
                        .values(
                            last_fetch_at=now,
                            last_fetch_status="failed",
                            last_fetch_error=error_msg,
                        )
                    )
                    session.commit()
                    results[model_id] = "failed"
                    logger.warning(
                        "prediction_fetch_quality_failed",
                        model_id=model_id,
                        model_name=model.model_name,
                        errors=quality_errors,
                    )
                    continue

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

                upsert_stmt = build_prediction_upsert_stmt(record_dicts)
                session.execute(upsert_stmt)

                fetch_status = "success" if len(valid_records) == 96 else "partial"
                error_msg = "; ".join(quality_errors[:5]) if quality_errors else None

                session.execute(
                    update(PredictionModel)
                    .where(PredictionModel.id == model.id)
                    .values(
                        last_fetch_at=now,
                        last_fetch_status=fetch_status,
                        last_fetch_error=error_msg,
                    )
                )
                session.commit()

                results[model_id] = fetch_status
                logger.info(
                    "prediction_fetch_result",
                    model_id=model_id,
                    model_name=model.model_name,
                    status=fetch_status,
                    records_count=len(valid_records),
                    prediction_date=prediction_date.isoformat(),
                )

            except Exception as e:
                session.rollback()
                error_msg = str(e)[:500]
                try:
                    session.execute(
                        update(PredictionModel)
                        .where(PredictionModel.id == model.id)
                        .values(
                            last_fetch_at=now,
                            last_fetch_status="failed",
                            last_fetch_error=error_msg,
                        )
                    )
                    session.commit()
                except Exception:
                    session.rollback()

                results[model_id] = "failed"
                logger.warning(
                    "prediction_fetch_exception",
                    model_id=model_id,
                    model_name=model.model_name,
                    error=error_msg,
                )

    return results
