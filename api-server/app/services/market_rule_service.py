from uuid import UUID

import structlog
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import BusinessError
from app.models.market_rule import ProvinceMarketRule
from app.models.user import User
from app.repositories.market_rule import MarketRuleRepository
from app.schemas.market_rule import (
    BandwidthParams,
    DeviationFormulaType,
    MarketRuleCreate,
    ProportionalParams,
    SteppedParams,
)
from app.services.audit_service import AuditService

logger = structlog.get_logger()

_FORMULA_PARAMS_SCHEMA: dict[str, type] = {
    "stepped": SteppedParams,
    "proportional": ProportionalParams,
    "bandwidth": BandwidthParams,
}

_FIELD_LABELS: dict[str, str] = {
    "exemption_ratio": "免考核比例",
    "base_rate": "基础倍率",
    "bandwidth_percent": "带宽百分比",
    "penalty_rate": "罚金系数",
    "steps": "阶梯列表",
    "lower": "下限",
    "upper": "上限",
    "rate": "倍率",
}

_ERROR_TYPE_TEMPLATES: dict[str, str] = {
    "less_than": "必须小于 {lt}",
    "greater_than": "必须大于 {gt}",
    "greater_than_equal": "不能小于 {ge}",
    "less_than_equal": "不能大于 {le}",
    "missing": "为必填项",
    "too_short": "至少需要 {min_length} 项",
}


def _format_validation_errors(exc: ValidationError) -> str:
    parts: list[str] = []
    for err in exc.errors():
        field_parts: list[str] = []
        for seg in err["loc"]:
            if isinstance(seg, str):
                field_parts.append(_FIELD_LABELS.get(seg, seg))
            elif isinstance(seg, int):
                field_parts.append(f"第{seg + 1}项")
        field_name = " > ".join(field_parts) if field_parts else "未知字段"

        err_type = err["type"]
        ctx = err.get("ctx", {})
        template = _ERROR_TYPE_TEMPLATES.get(err_type)
        if template:
            msg = template.format_map(ctx)
        else:
            msg = err.get("msg", "参数无效")

        parts.append(f"{field_name}{msg}")
    return "；".join(parts)


class MarketRuleService:
    def __init__(
        self,
        market_rule_repo: MarketRuleRepository,
        audit_service: AuditService,
    ):
        self.market_rule_repo = market_rule_repo
        self.audit_service = audit_service

    def _warn_if_no_ip(self, action: str, ip_address: str | None) -> None:
        if ip_address is None:
            logger.warning("audit_ip_missing", action=action, hint="非 HTTP 上下文调用，IP 地址缺失")

    def _validate_deviation_params(
        self, formula_type: str, params: dict
    ) -> None:
        schema_cls = _FORMULA_PARAMS_SCHEMA.get(formula_type)
        if not schema_cls:
            raise BusinessError(
                code="INVALID_DEVIATION_PARAMS",
                message=f"不支持的偏差考核公式类型: {formula_type}",
                status_code=422,
            )
        try:
            schema_cls(**params)
        except ValidationError as e:
            raise BusinessError(
                code="INVALID_DEVIATION_PARAMS",
                message=f"偏差考核公式参数不合法: {_format_validation_errors(e)}",
                status_code=422,
            ) from None

    async def create_or_update_market_rule(
        self,
        province: str,
        data: MarketRuleCreate,
        current_user: User,
        client_ip: str | None = None,
    ) -> ProvinceMarketRule:
        self._warn_if_no_ip("upsert_market_rule", client_ip)

        self._validate_deviation_params(
            data.deviation_formula_type, data.deviation_formula_params
        )

        existing = await self.market_rule_repo.get_by_province_for_update(province)

        if existing:
            changes_before: dict = {}
            changes_after: dict = {}

            update_fields = {
                "price_cap_upper": data.price_cap_upper,
                "price_cap_lower": data.price_cap_lower,
                "settlement_method": data.settlement_method,
                "deviation_formula_type": data.deviation_formula_type,
                "deviation_formula_params": data.deviation_formula_params,
            }

            for field, new_value in update_fields.items():
                old_value = getattr(existing, field)
                serialized_old = old_value if isinstance(old_value, (bool, int, float, dict, type(None))) else str(old_value)
                serialized_new = new_value if isinstance(new_value, (bool, int, float, dict, type(None))) else str(new_value)
                if serialized_old != serialized_new:
                    changes_before[field] = serialized_old
                    changes_after[field] = serialized_new
                    setattr(existing, field, new_value)

            if not existing.is_active:
                existing.is_active = True
                changes_before["is_active"] = False
                changes_after["is_active"] = True

            if changes_after:
                await self.market_rule_repo.session.flush()
                await self.market_rule_repo.session.refresh(existing)
                await self.audit_service.log_action(
                    user_id=current_user.id,
                    action="update_market_rule",
                    resource_type="province_market_rule",
                    resource_id=existing.id,
                    changes_before=changes_before,
                    changes_after=changes_after,
                    ip_address=client_ip,
                )
                logger.info(
                    "market_rule_updated",
                    province=province,
                    changes=list(changes_after.keys()),
                    admin=current_user.username,
                )

            return existing

        rule = ProvinceMarketRule(
            province=province,
            price_cap_upper=data.price_cap_upper,
            price_cap_lower=data.price_cap_lower,
            settlement_method=data.settlement_method,
            deviation_formula_type=data.deviation_formula_type,
            deviation_formula_params=data.deviation_formula_params,
        )
        try:
            created = await self.market_rule_repo.create(rule)
        except IntegrityError:
            raise BusinessError(
                code="PROVINCE_RULE_ALREADY_EXISTS",
                message=f"省份 {province} 的市场规则已存在",
                status_code=409,
            ) from None

        await self.audit_service.log_action(
            user_id=current_user.id,
            action="create_market_rule",
            resource_type="province_market_rule",
            resource_id=created.id,
            changes_after={
                "province": created.province,
                "price_cap_upper": str(created.price_cap_upper),
                "price_cap_lower": str(created.price_cap_lower),
                "settlement_method": created.settlement_method,
                "deviation_formula_type": created.deviation_formula_type,
                "deviation_formula_params": created.deviation_formula_params,
            },
            ip_address=client_ip,
        )

        logger.info(
            "market_rule_created",
            province=province,
            admin=current_user.username,
        )
        return created

    async def get_market_rule(self, province: str) -> ProvinceMarketRule:
        rule = await self.market_rule_repo.get_by_province(province)
        if not rule or not rule.is_active:
            raise BusinessError(
                code="MARKET_RULE_NOT_FOUND",
                message=f"省份 {province} 的市场规则不存在",
                status_code=404,
            )
        return rule

    async def list_market_rules(self) -> list[ProvinceMarketRule]:
        return await self.market_rule_repo.list_all_active()

    async def delete_market_rule(
        self,
        province: str,
        current_user: User,
        client_ip: str | None = None,
    ) -> None:
        self._warn_if_no_ip("delete_market_rule", client_ip)

        rule = await self.market_rule_repo.get_by_province_for_update(province)
        if not rule or not rule.is_active:
            raise BusinessError(
                code="MARKET_RULE_NOT_FOUND",
                message=f"省份 {province} 的市场规则不存在",
                status_code=404,
            )
        rule.is_active = False
        await self.market_rule_repo.session.flush()

        await self.audit_service.log_action(
            user_id=current_user.id,
            action="delete_market_rule",
            resource_type="province_market_rule",
            resource_id=rule.id,
            changes_before={"is_active": True},
            changes_after={"is_active": False},
            ip_address=client_ip,
        )

        logger.info(
            "market_rule_deactivated",
            province=province,
            admin=current_user.username,
        )

    @staticmethod
    def get_deviation_formula_templates() -> list[dict]:
        """返回可用的偏差考核公式模板列表。"""
        from rules.loader import load_province_config
        from rules.registry import registry

        templates = []
        for name in registry.list_names():
            config = load_province_config(name)
            templates.append({
                "province": name,
                "deviation_formula_type": config.get("deviation_formula_type", ""),
                "default_params": config.get("deviation_formula_params", {}),
            })
        return templates

    @staticmethod
    def get_default_params(province: str) -> dict:
        """从 JSON 配置加载省份默认参数作为模板预填。"""
        from rules.loader import load_province_config
        return load_province_config(province)
