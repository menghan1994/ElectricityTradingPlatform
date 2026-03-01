from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Numeric, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class ProvinceMarketRule(Base, IdMixin, TimestampMixin):
    __tablename__ = "province_market_rules"

    province: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    price_cap_upper: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_cap_lower: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    settlement_method: Mapped[str] = mapped_column(String(20), nullable=False)
    deviation_formula_type: Mapped[str] = mapped_column(String(20), nullable=False)
    deviation_formula_params: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    __table_args__ = (
        CheckConstraint(
            "price_cap_upper > price_cap_lower",
            name="ck_province_market_rules_price_cap",
        ),
        CheckConstraint(
            "price_cap_upper > 0 AND price_cap_lower >= 0",
            name="ck_province_market_rules_price_positive",
        ),
        CheckConstraint(
            "settlement_method IN ('spot', 'contract', 'hybrid')",
            name="ck_province_market_rules_settlement",
        ),
        CheckConstraint(
            "deviation_formula_type IN ('stepped', 'proportional', 'bandwidth')",
            name="ck_province_market_rules_deviation_type",
        ),
    )
