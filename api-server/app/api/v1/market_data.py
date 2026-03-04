from datetime import date
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.dependencies import require_roles
from app.core.ip_utils import get_client_ip
from app.models.user import User
from app.repositories.audit import AuditLogRepository
from app.repositories.market_data import (
    MarketClearingPriceRepository,
    MarketDataSourceRepository,
)
from app.schemas.market_data import (
    MarketClearingPriceListResponse,
    MarketClearingPriceRead,
    MarketDataFetchResult,
    MarketDataFreshnessListResponse,
    MarketDataSourceCreate,
    MarketDataSourceListResponse,
    MarketDataSourceRead,
    MarketDataSourceUpdate,
)
from app.services.audit_service import AuditService
from app.services.market_data_service import MarketDataService

router = APIRouter()


async def _get_redis_client() -> aioredis.Redis | None:
    try:
        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await client.ping()
        return client
    except Exception:
        return None


async def _get_market_data_service(
    session: AsyncSession = Depends(get_db_session),
) -> MarketDataService:
    price_repo = MarketClearingPriceRepository(session)
    source_repo = MarketDataSourceRepository(session)
    audit_repo = AuditLogRepository(session)
    audit_service = AuditService(audit_repo)
    redis_client = await _get_redis_client()
    return MarketDataService(price_repo, source_repo, audit_service, redis_client)


# --- 市场数据查询 ---


@router.get("", response_model=MarketClearingPriceListResponse)
async def list_market_data(
    province: str | None = Query(None),
    trading_date: date | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(96, ge=1, le=100),
    current_user: User = Depends(require_roles(["admin", "trader"])),
    service: MarketDataService = Depends(_get_market_data_service),
) -> MarketClearingPriceListResponse:
    records, total = await service.price_repo.list_paginated(
        province=province,
        trading_date=trading_date,
        page=page,
        page_size=page_size,
    )
    return MarketClearingPriceListResponse(
        items=[MarketClearingPriceRead.model_validate(r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
    )


# --- 数据新鲜度 ---


@router.get("/freshness", response_model=MarketDataFreshnessListResponse)
async def get_freshness(
    current_user: User = Depends(require_roles(["admin", "trader"])),
    service: MarketDataService = Depends(_get_market_data_service),
) -> MarketDataFreshnessListResponse:
    items = await service.check_all_freshness()
    return MarketDataFreshnessListResponse(items=items)


# --- 手动触发获取 ---


@router.post("/fetch", response_model=MarketDataFetchResult)
async def trigger_fetch(
    province: str = Query(...),
    trading_date: date = Query(...),
    current_user: User = Depends(require_roles(["admin"])),
    service: MarketDataService = Depends(_get_market_data_service),
) -> MarketDataFetchResult:
    try:
        records = await service.fetch_market_data(
            province=province,
            trading_date=trading_date,
            user_id=current_user.id,
        )
        return MarketDataFetchResult(
            province=province,
            trading_date=trading_date,
            records_count=len(records),
            status="success",
        )
    except Exception as e:
        return MarketDataFetchResult(
            province=province,
            trading_date=trading_date,
            records_count=0,
            status="failed",
            error_message=str(e),
        )


# --- 手动上传 ---


@router.post("/upload", response_model=MarketDataFetchResult)
async def upload_market_data(
    file: UploadFile,
    province: str = Query(...),
    current_user: User = Depends(require_roles(["admin"])),
    service: MarketDataService = Depends(_get_market_data_service),
) -> MarketDataFetchResult:
    import csv
    import io
    from decimal import Decimal, InvalidOperation

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    records: list[dict] = []
    total_rows = 0
    skipped_rows = 0
    for row in reader:
        total_rows += 1
        try:
            trading_date_str = row.get("trading_date") or row.get("交易日期", "")
            period_str = row.get("period") or row.get("时段", "")
            price_str = row.get("clearing_price") or row.get("出清价格", "")

            records.append({
                "trading_date": date.fromisoformat(trading_date_str.strip()),
                "period": int(period_str.strip()),
                "clearing_price": Decimal(price_str.strip()),
            })
        except (ValueError, InvalidOperation, KeyError):
            skipped_rows += 1
            continue

    if not records:
        return MarketDataFetchResult(
            province=province,
            trading_date=date.today(),
            records_count=0,
            status="failed",
            error_message=f"无法解析有效数据（共{total_rows}行，{skipped_rows}行格式错误）",
        )

    count = await service.import_market_data_from_records(
        province=province,
        records=records,
        user_id=current_user.id,
    )

    first_date = records[0]["trading_date"]
    error_msg = f"跳过{skipped_rows}行格式错误数据" if skipped_rows > 0 else None
    return MarketDataFetchResult(
        province=province,
        trading_date=first_date,
        records_count=count,
        status="success",
        error_message=error_msg,
    )


# --- 数据源 CRUD ---


@router.get("/sources", response_model=MarketDataSourceListResponse)
async def list_sources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: bool | None = Query(None),
    current_user: User = Depends(require_roles(["admin"])),
    service: MarketDataService = Depends(_get_market_data_service),
) -> MarketDataSourceListResponse:
    sources, total = await service.source_repo.list_all_paginated(
        page=page, page_size=page_size, is_active=is_active,
    )
    return MarketDataSourceListResponse(
        items=[MarketDataSourceRead.model_validate(s) for s in sources],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/sources", response_model=MarketDataSourceRead, status_code=201)
async def create_source(
    body: MarketDataSourceCreate,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    service: MarketDataService = Depends(_get_market_data_service),
) -> MarketDataSourceRead:
    source = await service.create_source(
        province=body.province,
        source_name=body.source_name,
        api_endpoint=body.api_endpoint,
        api_key=body.api_key,
        api_auth_type=body.api_auth_type,
        fetch_schedule=body.fetch_schedule,
        is_active=body.is_active,
        cache_ttl_seconds=body.cache_ttl_seconds,
        user_id=current_user.id,
    )
    return MarketDataSourceRead.model_validate(source)


@router.put("/sources/{source_id}", response_model=MarketDataSourceRead)
async def update_source(
    source_id: UUID,
    body: MarketDataSourceUpdate,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    service: MarketDataService = Depends(_get_market_data_service),
) -> MarketDataSourceRead:
    update_data = body.model_dump(exclude_unset=True)
    source = await service.update_source(
        source_id=source_id,
        update_data=update_data,
        user_id=current_user.id,
    )
    return MarketDataSourceRead.model_validate(source)


@router.delete("/sources/{source_id}", status_code=204)
async def delete_source(
    source_id: UUID,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    service: MarketDataService = Depends(_get_market_data_service),
) -> None:
    await service.delete_source(
        source_id=source_id,
        user_id=current_user.id,
    )
