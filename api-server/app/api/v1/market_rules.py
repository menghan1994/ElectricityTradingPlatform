from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.data_access import require_write_permission
from app.core.database import get_db_session
from app.core.dependencies import require_roles
from app.core.ip_utils import get_client_ip
from app.models.user import User
from app.repositories.audit import AuditLogRepository
from app.repositories.market_rule import MarketRuleRepository
from app.schemas.market_rule import MarketRuleCreate, MarketRuleRead
from app.schemas.station import Province
from app.services.audit_service import AuditService
from app.services.market_rule_service import MarketRuleService

router = APIRouter()


def _get_market_rule_service(
    session: AsyncSession = Depends(get_db_session),
) -> MarketRuleService:
    market_rule_repo = MarketRuleRepository(session)
    audit_repo = AuditLogRepository(session)
    audit_service = AuditService(audit_repo)
    return MarketRuleService(market_rule_repo, audit_service)


@router.get("", response_model=list[MarketRuleRead])
async def list_market_rules(
    current_user: User = Depends(require_roles(["admin"])),
    service: MarketRuleService = Depends(_get_market_rule_service),
) -> list[MarketRuleRead]:
    rules = await service.list_market_rules()
    return [MarketRuleRead.model_validate(r) for r in rules]


@router.get("/templates")
async def get_deviation_templates(
    current_user: User = Depends(require_roles(["admin"])),
) -> list[dict]:
    """返回偏差考核公式模板列表和默认参数。"""
    return MarketRuleService.get_deviation_formula_templates()


@router.get("/defaults/{province}")
async def get_province_defaults(
    province: Province,
    current_user: User = Depends(require_roles(["admin"])),
) -> dict:
    """获取指定省份的默认参数配置（用于模板预填）。"""
    return MarketRuleService.get_default_params(province)


@router.get("/{province}", response_model=MarketRuleRead)
async def get_market_rule(
    province: Province,
    current_user: User = Depends(require_roles(["admin"])),
    service: MarketRuleService = Depends(_get_market_rule_service),
) -> MarketRuleRead:
    rule = await service.get_market_rule(province)
    return MarketRuleRead.model_validate(rule)


@router.put("/{province}", response_model=MarketRuleRead)
async def upsert_market_rule(
    province: Province,
    body: MarketRuleCreate,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    _write_check: User = Depends(require_write_permission),
    service: MarketRuleService = Depends(_get_market_rule_service),
) -> MarketRuleRead:
    ip_address = get_client_ip(request)
    rule = await service.create_or_update_market_rule(
        province, body, current_user, ip_address,
    )
    return MarketRuleRead.model_validate(rule)


@router.delete("/{province}", status_code=204)
async def delete_market_rule(
    province: Province,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    _write_check: User = Depends(require_write_permission),
    service: MarketRuleService = Depends(_get_market_rule_service),
) -> None:
    ip_address = get_client_ip(request)
    await service.delete_market_rule(province, current_user, ip_address)
