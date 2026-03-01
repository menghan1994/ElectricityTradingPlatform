from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.station import Province

SettlementMethod = Literal["spot", "contract", "hybrid"]
DeviationFormulaType = Literal["stepped", "proportional", "bandwidth"]


# --- 偏差考核公式参数 schemas ---


class SteppedStep(BaseModel):
    lower: float = Field(..., ge=0, lt=1)
    upper: float = Field(..., gt=0, le=1)
    rate: float = Field(..., gt=0)

    @model_validator(mode="after")
    def validate_lower_less_than_upper(self) -> "SteppedStep":
        if self.lower >= self.upper:
            raise ValueError("阶梯下限必须小于上限")
        return self


class SteppedParams(BaseModel):
    exemption_ratio: float = Field(..., ge=0, lt=1)
    steps: list[SteppedStep] = Field(..., min_length=1)


class ProportionalParams(BaseModel):
    exemption_ratio: float = Field(..., ge=0, lt=1)
    base_rate: float = Field(..., gt=0)


class BandwidthParams(BaseModel):
    bandwidth_percent: float = Field(..., ge=0, lt=1)
    penalty_rate: float = Field(..., gt=0)


# --- 市场规则 CRUD schemas ---


class MarketRuleCreate(BaseModel):
    price_cap_upper: Decimal = Field(..., gt=0, decimal_places=2)
    price_cap_lower: Decimal = Field(..., ge=0, decimal_places=2)
    settlement_method: SettlementMethod
    deviation_formula_type: DeviationFormulaType
    deviation_formula_params: dict

    @model_validator(mode="after")
    def validate_price_cap_range(self) -> "MarketRuleCreate":
        if self.price_cap_upper <= self.price_cap_lower:
            raise ValueError("最高限价必须大于最低限价")
        return self



class MarketRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    province: str
    price_cap_upper: Decimal
    price_cap_lower: Decimal
    settlement_method: SettlementMethod
    deviation_formula_type: DeviationFormulaType
    deviation_formula_params: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime
