from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import require_roles
from app.models.user import User
from app.repositories.audit import AuditLogRepository
from app.repositories.prediction import PowerPredictionRepository, PredictionModelRepository
from app.schemas.prediction import (
    ConnectionTestResult,
    FetchResult,
    PowerPredictionListResponse,
    PowerPredictionRead,
    PredictionModelCreate,
    PredictionModelListResponse,
    PredictionModelRead,
    PredictionModelStatusListResponse,
    PredictionModelUpdate,
)
from app.services.audit_service import AuditService
from app.services.prediction_service import PredictionService

router = APIRouter()


async def _get_prediction_service(
    session: AsyncSession = Depends(get_db_session),
) -> PredictionService:
    model_repo = PredictionModelRepository(session)
    audit_repo = AuditLogRepository(session)
    audit_service = AuditService(audit_repo)
    prediction_repo = PowerPredictionRepository(session)
    return PredictionService(model_repo, audit_service, prediction_repo=prediction_repo)


async def _get_prediction_repo(
    session: AsyncSession = Depends(get_db_session),
) -> PowerPredictionRepository:
    return PowerPredictionRepository(session)


# --- 模型列表与状态（固定路径优先于路径参数） ---


@router.get("", response_model=PredictionModelListResponse)
async def list_prediction_models(
    station_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles(["admin", "trader"])),
    service: PredictionService = Depends(_get_prediction_service),
) -> PredictionModelListResponse:
    models, total = await service.list_models(
        station_id=station_id, page=page, page_size=page_size,
    )
    return PredictionModelListResponse(
        items=[PredictionModelRead.from_model(m) for m in models],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/status", response_model=PredictionModelStatusListResponse)
async def get_model_statuses(
    current_user: User = Depends(require_roles(["admin", "trader"])),
    service: PredictionService = Depends(_get_prediction_service),
) -> PredictionModelStatusListResponse:
    statuses = await service.get_all_model_statuses()
    return PredictionModelStatusListResponse(items=statuses)


@router.post("", response_model=PredictionModelRead, status_code=201)
async def create_prediction_model(
    body: PredictionModelCreate,
    current_user: User = Depends(require_roles(["admin"])),
    service: PredictionService = Depends(_get_prediction_service),
) -> PredictionModelRead:
    model = await service.create_model(
        model_name=body.model_name,
        model_type=body.model_type,
        api_endpoint=body.api_endpoint,
        api_key=body.api_key,
        api_auth_type=body.api_auth_type,
        call_frequency_cron=body.call_frequency_cron,
        timeout_seconds=body.timeout_seconds,
        station_id=body.station_id,
        user_id=current_user.id,
    )
    return PredictionModelRead.from_model(model)


# --- 路径参数端点 ---


@router.get("/{model_id}", response_model=PredictionModelRead)
async def get_prediction_model(
    model_id: UUID,
    current_user: User = Depends(require_roles(["admin", "trader"])),
    service: PredictionService = Depends(_get_prediction_service),
) -> PredictionModelRead:
    model = await service.get_model(model_id)
    return PredictionModelRead.from_model(model)


@router.put("/{model_id}", response_model=PredictionModelRead)
async def update_prediction_model(
    model_id: UUID,
    body: PredictionModelUpdate,
    current_user: User = Depends(require_roles(["admin"])),
    service: PredictionService = Depends(_get_prediction_service),
) -> PredictionModelRead:
    update_data = body.model_dump(exclude_unset=True)
    model = await service.update_model(
        model_id=model_id,
        update_data=update_data,
        user_id=current_user.id,
    )
    return PredictionModelRead.from_model(model)


@router.delete("/{model_id}", status_code=204)
async def delete_prediction_model(
    model_id: UUID,
    current_user: User = Depends(require_roles(["admin"])),
    service: PredictionService = Depends(_get_prediction_service),
) -> None:
    await service.delete_model(
        model_id=model_id,
        user_id=current_user.id,
    )


@router.post("/{model_id}/test-connection", response_model=ConnectionTestResult)
async def test_connection(
    model_id: UUID,
    current_user: User = Depends(require_roles(["admin"])),
    service: PredictionService = Depends(_get_prediction_service),
) -> ConnectionTestResult:
    return await service.test_connection(model_id)


@router.post("/{model_id}/fetch", response_model=FetchResult)
async def trigger_fetch(
    model_id: UUID,
    prediction_date: date | None = Body(None, embed=True),
    current_user: User = Depends(require_roles(["admin"])),
    service: PredictionService = Depends(_get_prediction_service),
) -> FetchResult:
    """手动触发指定模型的预测数据拉取。"""
    if prediction_date is None:
        prediction_date = date.today() + timedelta(days=1)
    return await service.fetch_predictions(
        model_id=model_id,
        prediction_date=prediction_date,
        user_id=current_user.id,
    )


@router.get("/{model_id}/predictions", response_model=PowerPredictionListResponse)
async def get_model_predictions(
    model_id: UUID,
    prediction_date: date = Query(...),
    current_user: User = Depends(require_roles(["admin", "trader"])),
    prediction_repo: PowerPredictionRepository = Depends(_get_prediction_repo),
    service: PredictionService = Depends(_get_prediction_service),
) -> PowerPredictionListResponse:
    """查询指定模型的预测数据。"""
    model = await service.get_model(model_id)
    predictions = await prediction_repo.get_by_station_date_model(
        station_id=model.station_id,
        prediction_date=prediction_date,
        model_id=model_id,
    )
    items = [PowerPredictionRead.model_validate(p) for p in predictions]
    return PowerPredictionListResponse(items=items, total=len(items))
